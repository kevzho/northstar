/**
 * Frontend API client.
 *
 * This module is the single place that talks to the Meridian FastAPI backend
 * and (for auth) to Supabase. Every function here is currently a typed stub
 * because the backend routers do not exist yet. When a real endpoint lands
 * (Day 3 for /match, Day 5 for mentors), replace the TODO body with the fetch
 * call and keep the same return type so components do not change.
 *
 * Conventions:
 *   - All endpoints live under NEXT_PUBLIC_API_URL (set in .env.local).
 *   - The Supabase access token is attached as `Authorization: Bearer ...`
 *     by a small helper that pulls the live session from lib/supabase.
 */

import { supabase } from "./supabase";
import type { MatchResult, Opportunity, Bookmark, StudentProfile } from "./types";

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
  profile: Pick<StudentProfile, "name" | "grade" | "interests" | "goals" | "onboarded"> & { consent?: boolean },
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
