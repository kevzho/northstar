/**
 * Frontend API client.
 *
 * This module is the single place that talks to the Northstar FastAPI backend
 * and (for auth) to Supabase. Every function here is wired to a live route in
 * backend/app/main.py.
 *
 * Conventions:
 *   - All endpoints live under NEXT_PUBLIC_API_URL (set in .env.local). Every
 *     caller must run in the browser: the access token comes from the Supabase
 *     session, which supabase-js keeps in localStorage. Calling these from a
 *     server component sends an anonymous request and gets a 401 back.
 *   - The Supabase access token is attached as `Authorization: Bearer ...`
 *     by a small helper that pulls the live session from lib/supabase.
 */

import { supabase } from "./supabase";
import type {
  MatchResult,
  Opportunity,
  Bookmark,
  StudentProfile,
  Outcome,
  ProjectRec,
  Mission,
  MissionCompletion,
  TimelineEvent,
  PublicProfile,
} from "./types";

export type Mentor = {
  id: string;
  name: string;
  email: string;
  bio: string;
  expertise: string[];
};

export type MentorScore = {
  mentor_id: string;
  score: number;
  explanation: string;
};

export type MentorMatch = {
  mentor: Mentor;
  score: MentorScore;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

/**
 * Build a JSON fetch request with the current Supabase access token attached.
 * When no session exists the caller receives a 401 from the backend — the
 * UI gate already runs useAuth() before this, so that path is rare.
 */
/** An HTTP failure, with the status and the server's message kept intact. */
export type ApiError = Error & { status: number; detail: string };

export function isApiError(error: unknown): error is ApiError {
  return error instanceof Error && typeof (error as ApiError).status === "number";
}

export async function authedFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    // Carry the server's own message out with the error. Some refusals are
    // written for the student to read — /advisor's 429 says which budget ran
    // out and when it resets — and throwing only the status discards them.
    let detail = "";
    try {
      detail = ((await res.clone().json()) as { detail?: string }).detail ?? "";
    } catch {
      // Non-JSON body (a proxy error page, say); the status has to speak.
    }
    const error = new Error(
      `API ${res.status} on ${path}${detail ? `: ${detail}` : ""}`,
    ) as ApiError;
    error.status = res.status;
    error.detail = detail;
    throw error;
  }
  return res;
}

/**
 * Create or update the signed-in student's profile.
 *
 * id and email are derived by the backend from the JWT; the caller only
 * supplies the editable fields from the onboarding form.
 */
export async function saveStudentProfile(
  profile: Pick<StudentProfile, "name" | "grade" | "interests" | "goals" | "onboarded"> & {
    /** Omitted on stub upserts; the backend defaults to high_school. */
    audience?: StudentProfile["audience"];
    location_pref?: StudentProfile["location_pref"];
    consent?: boolean;
    /** When present it replaces the stored links; absent leaves them alone. */
    social_links?: Record<string, string>;
  },
): Promise<StudentProfile> {
  const row = await (await authedFetch("/students", {
    method: "POST",
    body: JSON.stringify(profile),
  })).json();
  // interests, goals, grade, audience and location_pref are all scoring
  // inputs, so a profile edit changes the ranking.
  invalidateMatches();
  return row;
}

/**
 * Fetch ranked opportunities for the signed-in student.
 *
 * Calls GET /match on the FastAPI backend, which runs the TF-IDF scoring
 * pipeline and returns MatchResult[] sorted by score desc.
 *
 * Cached in memory for MATCH_CACHE_MS. Three pages call this — the dashboard,
 * /opportunities and /plan — and a student moving between them in one session
 * re-ran the whole pipeline each time: a catalog read, four more queries, and
 * a write, to return a list that had not changed. The ranking only moves when
 * the profile, a bookmark, a dismissal or an outcome changes, and each of
 * those goes through a mutation below that clears this.
 *
 * Deliberately a module-level variable, not sessionStorage: the point is to
 * collapse duplicate calls inside one navigation session, and it should not
 * survive a reload — a reload is a student asking for fresh data.
 */
const MATCH_CACHE_MS = 60_000;
let matchCache: { at: number; inflight: Promise<MatchResult[]> } | null = null;

/** Drop the cached ranking. Called by every mutation that can change it. */
export function invalidateMatches(): void {
  matchCache = null;
}

export async function fetchMatches(): Promise<MatchResult[]> {
  const fresh = matchCache && Date.now() - matchCache.at < MATCH_CACHE_MS;
  if (fresh && matchCache) return matchCache.inflight;

  // Store the promise, not the result, so two pages mounting at once share
  // one request instead of racing and firing two.
  const inflight = (async () => (await authedFetch("/match")).json())();
  matchCache = { at: Date.now(), inflight };
  try {
    return await inflight;
  } catch (error) {
    matchCache = null; // never cache a failure
    throw error;
  }
}

/**
 * Fetch a single opportunity by id. Used by the opportunity detail page.
 */
export async function fetchOpportunity(id: string): Promise<Opportunity | null> {
  try {
    return (await authedFetch(`/opportunities/${id}`)).json();
  } catch {
    // A 404 or network error → null, which the detail page renders as
    // "Opportunity not found".
    return null;
  }
}

/**
 * List the current student's bookmarks.
 */
export async function fetchBookmarks(): Promise<Bookmark[]> {
  return (await authedFetch("/bookmarks")).json();
}

/**
 * Bookmark an opportunity.
 */
export async function bookmarkOpportunity(opportunityId: string): Promise<Bookmark> {
  const saved = await (await authedFetch("/bookmarks", {
    method: "POST",
    body: JSON.stringify({ opportunity_id: opportunityId }),
  })).json();
  invalidateMatches(); // bookmarks feed the field booster in match.py
  return saved;
}

/**
 * Remove a bookmark by opportunity id.
 */
export async function removeBookmark(opportunityId: string): Promise<void> {
  await authedFetch(`/bookmarks/${opportunityId}`, { method: "DELETE" });
  invalidateMatches(); // bookmarks feed the field booster in match.py
}

/**
 * Fetch ranked mentor recommendations for the signed-in student.
 *
 * Calls GET /mentors on the FastAPI backend, which runs the TF-IDF mentor
 * matching engine and returns MentorMatch[] sorted by score desc.
 */
export async function fetchMentors(): Promise<MentorMatch[]> {
  return (await authedFetch("/mentors")).json();
}

/**
 * List the outcomes this student has already logged, newest first.
 *
 * Calls GET /outcomes. Used to show outcome history so the feedback loop
 * (outcomes → pathway_edges weights, migration_004) is visible in the demo
 * rather than silent.
 */
export async function fetchOutcomes(): Promise<Outcome[]> {
  return (await authedFetch("/outcomes")).json();
}

/**
 * Log a student's outcome for a bookmarked opportunity.
 */
export async function logOutcome(
  opportunityId: string,
  status: string,
  impactNotes?: string,
): Promise<{ id: string }> {
  const logged = await (await authedFetch("/outcomes", {
    method: "POST",
    body: JSON.stringify({
      opportunity_id: opportunityId,
      status,
      impact_notes: impactNotes ?? null,
    }),
  })).json();
  invalidateMatches(); // outcomes feed the ALS collaborative term
  return logged;
}

/**
 * Fetch ranked GitHub project recommendations for the given fields.
 * The backend caps fields at three and falls back to interdisciplinary.
 */
export async function fetchProjects(fields: string[]): Promise<ProjectRec[]> {
  const query = fields.length ? `?fields=${fields.join(",")}` : "";
  return (await authedFetch(`/projects${query}`)).json();
}

/**
 * Sync the quiz's trait + field scores to the student row so matching can
 * weight the field boost by interest share. Fire-and-forget from the
 * caller's perspective; only signed-in students have a row to sync to.
 */
export async function syncAssessmentProfile(
  trait_scores: Record<string, number>,
  field_scores: Record<string, number>,
): Promise<void> {
  await authedFetch("/assessment-profile", {
    method: "POST",
    body: JSON.stringify({ trait_scores, field_scores }),
  });
  invalidateMatches(); // field_scores scale the field booster
}

/** Opportunity ids the student marked "not for me". */
export async function fetchDismissals(): Promise<{ opportunity_id: string }[]> {
  return (await authedFetch("/dismissals")).json();
}

export async function dismissOpportunity(opportunityId: string): Promise<void> {
  await authedFetch("/dismissals", {
    method: "POST",
    body: JSON.stringify({ opportunity_id: opportunityId }),
  });
  invalidateMatches(); // dismissals remove rows from the ranking entirely
}

export async function undoDismissal(opportunityId: string): Promise<void> {
  await authedFetch(`/dismissals/${opportunityId}`, { method: "DELETE" });
  invalidateMatches();
}

/** Proof missions, optionally for one archetype (future path). */
export async function fetchMissions(archetype?: string): Promise<Mission[]> {
  const query = archetype ? `?archetype=${encodeURIComponent(archetype)}` : "";
  return (await authedFetch(`/missions${query}`)).json();
}

/** The student's completed missions. */
export async function fetchMissionCompletions(): Promise<MissionCompletion[]> {
  return (await authedFetch("/missions/completions")).json();
}

/** Record mission evidence; idempotent per (student, mission). */
export async function completeMission(
  missionId: string,
  evidence: string,
): Promise<MissionCompletion> {
  return (await authedFetch(`/missions/${missionId}/complete`, {
    method: "POST",
    body: JSON.stringify({ evidence }),
  })).json();
}

/** The evidence timeline: every recorded step, newest first. */
export async function fetchTimeline(): Promise<TimelineEvent[]> {
  return (await authedFetch("/timeline")).json();
}

/**
 * One grounded advisor exchange.
 *
 * 503 when the feature is unconfigured; 429 when a spend cap is hit, with a
 * student-readable reason in `detail`. `cached` marks an answer replayed
 * from a previous identical question — those cost no LLM credits.
 */
export async function askAdvisor(question: string): Promise<{
  answer: string;
  sources: {
    n: number;
    title: string;
    field: string;
    type: string;
    deadline: string | null;
    url: string;
  }[];
  cached?: boolean;
}> {
  return (await authedFetch("/advisor", {
    method: "POST",
    body: JSON.stringify({ question }),
  })).json();
}

// ---------------------------------------------------------------------------
// Sharing + friends
// ---------------------------------------------------------------------------

/** Set the public handle and/or the share toggle. 409 = handle taken. */
export async function updateSharing(update: {
  handle?: string;
  public_profile?: boolean;
}): Promise<{ handle: string | null; public_profile: boolean }> {
  return (await authedFetch("/sharing", {
    method: "POST",
    body: JSON.stringify(update),
  })).json();
}

/** A public record — no auth; 404 for private or unknown handles. */
export async function fetchPublicProfile(handle: string): Promise<PublicProfile> {
  const res = await fetch(`${API_URL}/public/${encodeURIComponent(handle)}`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

/** Persist the charted path so friends can compare career choices. */
export async function syncChosenPath(
  archetypeId: string,
  kind: string,
): Promise<void> {
  await authedFetch("/chosen-path", {
    method: "POST",
    body: JSON.stringify({ archetype_id: archetypeId, kind }),
  });
}

export type FriendEntry = {
  id: string;
  student_id: string;
  name: string;
  handle: string | null;
  direction: "sent" | "received";
};

export async function fetchFriends(): Promise<{
  accepted: FriendEntry[];
  pending: FriendEntry[];
}> {
  return (await authedFetch("/friends")).json();
}

export async function sendFriendRequest(handle: string): Promise<{ status: string }> {
  return (await authedFetch("/friends", {
    method: "POST",
    body: JSON.stringify({ handle }),
  })).json();
}

export async function acceptFriend(friendshipId: string): Promise<void> {
  await authedFetch(`/friends/${friendshipId}/accept`, { method: "POST" });
}

export async function removeFriend(friendshipId: string): Promise<void> {
  await authedFetch(`/friends/${friendshipId}`, { method: "DELETE" });
}

export type ComparedRecord = {
  handle: string | null;
  name: string;
  audience: string;
  trait_scores: Record<string, number> | null;
  field_scores: Record<string, number> | null;
  chosen_archetype: string | null;
  chosen_kind: string | null;
  missions_completed: number;
  outcome_counts: Record<string, number>;
};

export async function compareWithFriend(
  studentId: string,
): Promise<{ me: ComparedRecord; friend: ComparedRecord }> {
  return (await authedFetch(`/friends/${studentId}/compare`)).json();
}

export type Peer = {
  student_id: string;
  name: string;
  handle: string | null;
  shared_fields: string[];
  chosen_archetype: string | null;
  missions_completed: number;
  reasons: string[];
};

/** Opted-in peers who share the student's interests, ranked. */
export async function fetchDiscover(): Promise<Peer[]> {
  return (await authedFetch("/discover")).json();
}

// ---------------------------------------------------------------------------
// Team up (mutual-match collaborators) + safety
// ---------------------------------------------------------------------------

export type TeamupSettings = { enabled: boolean; pitch: string };

export async function fetchTeamupSettings(): Promise<TeamupSettings> {
  return (await authedFetch("/teamup/settings")).json();
}

export async function updateTeamupSettings(update: {
  enabled?: boolean;
  pitch?: string;
}): Promise<TeamupSettings> {
  return (await authedFetch("/teamup/settings", {
    method: "POST",
    body: JSON.stringify(update),
  })).json();
}

export type TeamupCandidate = {
  student_id: string;
  name: string;
  handle: string | null;
  grade: number | null;
  fields: string[];
  chosen_archetype: string | null;
  pitch: string;
  reasons: string[];
  missions_completed: number;
};

/** Ranked collaborator candidates; 409 until the student opts in. */
export async function fetchTeamupCandidates(): Promise<TeamupCandidate[]> {
  return (await authedFetch("/teamup/candidates")).json();
}

/** Interested/passed on a candidate; matched=true means you're connected. */
export async function sendTeamupInterest(
  studentId: string,
  decision: "interested" | "passed",
): Promise<{ matched: boolean }> {
  return (await authedFetch("/teamup/interest", {
    method: "POST",
    body: JSON.stringify({ student_id: studentId, decision }),
  })).json();
}

export type ReportReason =
  | "inappropriate"
  | "harassment"
  | "impersonation"
  | "spam"
  | "other";

/** File a safety report; the reported student never sees who filed. */
export async function reportStudent(input: {
  student_id?: string;
  handle?: string;
  reason: ReportReason;
  details?: string;
}): Promise<void> {
  await authedFetch("/report", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/** Hard wall: removes the connection and hides both students everywhere. */
export async function blockStudent(studentId: string): Promise<void> {
  await authedFetch("/block", {
    method: "POST",
    body: JSON.stringify({ student_id: studentId }),
  });
}

/** The full opportunity bank — every entry, unranked (GET /catalog). */
export async function fetchCatalog(): Promise<Opportunity[]> {
  return (await authedFetch("/catalog")).json();
}

/**
 * The high-school shelf, without an account.
 *
 * Every catalog route was auth-gated until 2026-10-05, so a visitor who clicked
 * "Opportunities" before signing up got a heading and nothing: /opportunities,
 * /discover and /plan each rendered zero rows while the API answered 401. That
 * reads as broken rather than as gated, and the shelf is the strongest thing
 * this project has to show someone deciding whether to make an account.
 *
 * A plain fetch, not authedFetch: there is no session to attach, and sending an
 * Authorization header of `undefined` is how a public route starts 401ing for
 * the people it exists for. The server returns an allowlist of fields — no
 * curation bookkeeping — and marks each row `is_open` so the client does not
 * re-derive today's date.
 */
export async function fetchPublicCatalog(): Promise<Opportunity[]> {
  const res = await fetch(`${API_URL}/catalog/public`, {
    headers: { "content-type": "application/json" },
  });
  if (!res.ok) return [];
  return res.json();
}

/** One free, verified learning resource for a spine skill rung. */
export type LearningResource = {
  id: string;
  title: string;
  host: string;
  url: string;
  kind: string;
  skill_key: string;
  skill_label: string;
  effort: string;
  prerequisite: string;
  why_this_one: string;
  free_evidence: string;
  verified_at: string | null;
};

/**
 * Free learning resources for one spine skill rung.
 *
 * The plan's skill step used to be an instruction with nowhere to go — "run a
 * focused 5-hour sprint on statistics" — which is only useful to a student who
 * already knew where to learn statistics. This is the where.
 *
 * Returns [] rather than throwing: a plan that renders without its resources
 * is still a plan, and this is the one call on the page that is additive.
 */
export async function fetchResources(
  skillKey: string,
): Promise<LearningResource[]> {
  if (!skillKey) return [];
  try {
    return await (
      await authedFetch(`/resources?skill=${encodeURIComponent(skillKey)}`)
    ).json();
  } catch {
    return [];
  }
}

/** One step in a student's roadmap. Provenance ids, never bare strings. */
export type RoadmapStep = {
  category: "skill" | "project" | "outreach" | "application";
  title: string;
  step_key: string;
  edge_reason: "eligibility" | "window" | "artifact" | "ladder" | "evidence";
  edge_note: string;
  opportunity_id: string | null;
  resource_id: string | null;
  mission_id: string | null;
  timeframe: "week" | "month";
  due_in_months: number;
  phase_index: number;
  phase_label: string;
  ordinal: number;
};

export type RoadmapPhase = { label: string; steps: RoadmapStep[] };

/** A program a student is not yet eligible for, with the grade it opens at. */
export type RoadmapHorizon = {
  title: string;
  opens_at_grade: number;
  opportunity_id: string;
  edge_reason: string;
  edge_note: string;
};

export type Roadmap = {
  horizon_months: number;
  grade: number | null;
  phases: RoadmapPhase[];
  horizon: RoadmapHorizon[];
  notes: { dated_steps: number; authored_edges: number; outcomes_logged: number };
  archetype_id: string;
  has_spine: boolean;
  resource_count: number;
  /** Who wrote the build/publish steps: one of 24 authored spines, or this student's own. */
  spine_source: "authored" | "generated";
  /**
   * The authored path names a skill rung with no verified resource behind it,
   * so the learn step renders as nothing. True for 12 of the 24 archetypes,
   * which is when offering a written-for-you path is a fix rather than a nag.
   */
  spine_hollow: boolean;
};

/** The build/publish steps rewritten for one student. */
export type GeneratedSpine = {
  project: string;
  publish: string;
  skill: string;
  skillKey: string;
  source: "generated";
  regenerated: boolean;
};

/**
 * Ask for a different path, saying why.
 *
 * The reason is the point, not a formality: it goes into the prompt with the
 * plan being turned down, and the model is told to write something genuinely
 * different rather than the same idea reworded.
 *
 * Throws with the server's own message, because every refusal here is one a
 * student should read — out of budget, model unreachable, or a path that came
 * back pointing at a skill with nothing behind it. In all three their current
 * path is unchanged, and saying so is more useful than a generic failure.
 */
export async function regenerateSpine(reason: string): Promise<GeneratedSpine> {
  const response = await authedFetch("/roadmap/spine", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) {
    const detail = await response
      .json()
      .then((body) => body?.detail)
      .catch(() => null);
    throw new Error(
      typeof detail === "string"
        ? detail
        : "Could not write a new path just now. Your current one is unchanged.",
    );
  }
  return response.json();
}

/**
 * The student's sequenced roadmap — what to do, in order.
 *
 * Returns null rather than throwing, so /plan can fall back to the client-side
 * generatePlan() when signed out or when the backend is unreachable. A student
 * who is not signed in still gets a plan; it just has no application steps.
 */
export async function fetchRoadmap(): Promise<Roadmap | null> {
  try {
    return await (await authedFetch("/roadmap")).json();
  } catch {
    return null;
  }
}
