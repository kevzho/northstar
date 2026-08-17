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
    throw new Error(`API ${res.status} on ${path}`);
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
  },
): Promise<StudentProfile> {
  return (await authedFetch("/students", {
    method: "POST",
    body: JSON.stringify(profile),
  })).json();
}

/**
 * Fetch ranked opportunities for the signed-in student.
 *
 * Calls GET /match on the FastAPI backend, which runs the TF-IDF scoring
 * pipeline and returns MatchResult[] sorted by score desc.
 */
export async function fetchMatches(): Promise<MatchResult[]> {
  return (await authedFetch("/match")).json();
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
  return (await authedFetch("/bookmarks", {
    method: "POST",
    body: JSON.stringify({ opportunity_id: opportunityId }),
  })).json();
}

/**
 * Remove a bookmark by opportunity id.
 */
export async function removeBookmark(opportunityId: string): Promise<void> {
  await authedFetch(`/bookmarks/${opportunityId}`, { method: "DELETE" });
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
  return (await authedFetch("/outcomes", {
    method: "POST",
    body: JSON.stringify({
      opportunity_id: opportunityId,
      status,
      impact_notes: impactNotes ?? null,
    }),
  })).json();
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
}

export async function undoDismissal(opportunityId: string): Promise<void> {
  await authedFetch(`/dismissals/${opportunityId}`, { method: "DELETE" });
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

/** One grounded advisor exchange; 503 when the feature is unconfigured. */
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
