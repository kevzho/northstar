/**
 * Shared domain types for Northstar.
 *
 * These intentionally mirror the Northstar Supabase schema (Day 2 migration)
 * rather than the interim Northstar V1 schema, so the UI is already typed
 * against the shape the backend will serve. No runtime data exists for any of
 * these types yet; they are compile-time contracts only.
 */

export type OpportunityField =
  | "cs"
  | "biology"
  | "math"
  | "physics"
  | "engineering"
  | "interdisciplinary";

export type OpportunityType =
  | "program"
  | "scholarship"
  | "competition"
  | "mentorship";

export type DemographicEligibility = "first_gen" | "urm" | "women_only" | "any";

export type Opportunity = {
  id: string;
  title: string;
  host: string;
  field: OpportunityField;
  type: OpportunityType;
  /** Short marketing blurb used on cards. */
  blurb: string;
  /** Long description shown on the detail page. */
  description: string;
  /** ISO date string or null when the deadline is rolling. */
  deadline: string | null;
  /** Program cost in USD; 0 means fully funded. */
  cost: number;
  grade_min: number;
  grade_max: number;
  url: string;
  tags: string[];
  /** Optional geographic location for map placement. */
  location: string | null;
};

export type MatchScore = {
  opportunity_id: string;
  /** TF-IDF cosine similarity in [0, 1]. */
  score: number;
  /** One-line, human-readable explanation for the judge-facing demo. */
  explanation: string;
};

export type MatchResult = {
  opportunity: Opportunity;
  score: MatchScore;
};

export type Bookmark = {
  id: string;
  opportunity_id: string;
  created_at: string;
};

export type OutcomeStatus =
  | "accepted"
  | "rejected"
  | "waitlisted"
  | "withdrew"
  | "completed";

/** A student-reported result, mirroring backend/app/schemas.py Outcome. */
export type Outcome = {
  id: string;
  opportunity_id: string;
  status: OutcomeStatus;
  impact_notes: string | null;
  created_at: string | null;
};

export type Audience = "high_school" | "college";

export type StudentProfile = {
  id: string;
  name: string | null;
  email: string | null;
  grade: string | null;
  interests: string[];
  goals: string | null;
  /** Which catalog shelf this student browses. */
  audience: Audience;
  /** Quiz outputs synced via POST /assessment-profile; null until synced. */
  trait_scores: Record<string, number> | null;
  field_scores: Record<string, number> | null;
  onboarded: boolean;
  /** ISO 8601 timestamp when the student accepted the IRB-style data
   * policy during onboarding, or null if consent has not been recorded. */
  consented_at: string | null;
};

/** A GitHub repository recommendation from GET /projects. */
export type ProjectRec = {
  field: OpportunityField;
  score: number;
  explanation: string;
  repo: {
    full_name: string;
    html_url: string;
    description: string;
    stars: number;
    language: string;
    topics: string[];
    good_first_issues_url: string;
  };
};
