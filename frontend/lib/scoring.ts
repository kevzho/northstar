/**
 * Assessment scoring — turns answers into trait scores and future paths.
 *
 * All of the inputs already existed: every choice in `lib/assessment.ts` carries
 * its own trait deltas, and every archetype in `lib/archetypes.ts` carries a
 * six-dimension trait vector. Nothing here invents new weights; it only
 * aggregates the numbers already written in those two files.
 *
 * The three steps, each deliberately simple enough to explain out loud:
 *
 *   1. Sum the deltas of the chosen answers per trait.
 *   2. Normalize each trait by the maximum that trait could have scored if
 *      every answer had been its strongest option → a 0-100 score. Dividing by
 *      the achievable maximum (not a fixed constant) keeps traits comparable
 *      even though they appear in different numbers of questions.
 *   3. Rank archetypes by cosine similarity between the student's trait vector
 *      and the archetype's, then label three of them:
 *        - safe          → the closest archetype
 *        - ambitious     → of the rest, the one that demands the most overall
 *        - unconventional→ of the rest, the one pointing furthest from "safe"
 *
 * Every number is tunable in one place. If the scoring design changes, change
 * it here and in the docstring — nothing else reads the raw deltas.
 */

import {
  LIKERT_VALUES,
  assessmentQuestions,
  likertWeight,
  type AssessmentQuestion,
  type FieldDeltas,
  type LikertValue,
  type TraitDeltas,
  type TraitKey,
} from "./assessment";
import { archetypes, type Archetype } from "./archetypes";
import type { OpportunityField } from "./types";

export type TraitScores = Record<TraitKey, number>;

/**
 * questionId → the chosen choice id, or a Likert rating stored as "1".."5".
 *
 * Ratings are kept as strings so the stored shape stays a flat
 * Record<string, string>: localStorage, `writeAnswers`, and the profile
 * sync all keep working untouched, and `isComplete`'s truthiness check
 * stays valid (no rating is ever 0).
 */
export type AssessmentAnswers = Record<string, string>;

/** "1".."5" → a LikertValue; anything else → null. */
export function parseLikert(raw: string): LikertValue | null {
  const value = Number(raw);
  return (LIKERT_VALUES as readonly number[]).includes(value)
    ? (value as LikertValue)
    : null;
}

/**
 * What one answer actually pays out. A pick pays its choice's deltas in
 * full; a rating pays the share `likertWeight` assigns it. Returning null
 * for an unrecognized answer is what makes stale stored answers inert
 * rather than throwing.
 */
function contribution(
  question: AssessmentQuestion,
  answer: string,
): { traits: TraitDeltas; fields?: FieldDeltas; weight: number } | null {
  if (question.kind === "likert") {
    const value = parseLikert(answer);
    if (value === null) return null;
    return {
      traits: question.traits,
      fields: question.fields,
      weight: likertWeight(value, question.reverse),
    };
  }
  const choice = question.choices.find((c) => c.id === answer);
  if (!choice) return null;
  return { traits: choice.traits, fields: choice.fields, weight: 1 };
}

export const TRAIT_KEYS: TraitKey[] = [
  "builder",
  "analyst",
  "riskTolerance",
  "ambiguityComfort",
  "collaboration",
  "executionTempo",
];

const ZERO: TraitScores = {
  builder: 0,
  analyst: 0,
  riskTolerance: 0,
  ambiguityComfort: 0,
  collaboration: 0,
  executionTempo: 0,
};

/**
 * The most each trait could accumulate: for every question, the largest delta
 * that trait carries across that question's choices.
 */
function maximumPossible(): TraitScores {
  const max = { ...ZERO };
  for (const question of assessmentQuestions) {
    for (const trait of TRAIT_KEYS) {
      // A rating question tops out at its own delta (paid at "Strongly
      // agree", or at "Strongly disagree" when reverse-coded); a pick tops
      // out at the largest delta any one of its options carries.
      const best =
        question.kind === "likert"
          ? Math.max(0, question.traits[trait] ?? 0)
          : Math.max(
              0,
              ...question.choices.map((choice) => choice.traits[trait] ?? 0),
            );
      max[trait] += best;
    }
  }
  return max;
}

const MAXIMUM = maximumPossible();

/** Sum the chosen answers' deltas, then normalize each trait to 0-100. */
export function scoreTraits(answers: AssessmentAnswers): TraitScores {
  const raw = { ...ZERO };

  for (const question of assessmentQuestions) {
    const answer = answers[question.id];
    if (!answer) continue;
    const paid = contribution(question, answer);
    if (!paid) continue;
    for (const trait of TRAIT_KEYS) {
      raw[trait] += (paid.traits[trait] ?? 0) * paid.weight;
    }
  }

  const scores = { ...ZERO };
  for (const trait of TRAIT_KEYS) {
    const ceiling = MAXIMUM[trait];
    scores[trait] = ceiling > 0 ? Math.round((raw[trait] / ceiling) * 100) : 0;
  }
  return scores;
}

// ---------------------------------------------------------------------------
// Field interest — scored from the field-signal questions: the picks
// (q4-q6) and the interest statements (l7-l14).
// ---------------------------------------------------------------------------

export const FIELD_KEYS: OpportunityField[] = [
  "cs",
  "biology",
  "math",
  "physics",
  "engineering",
  "interdisciplinary",
  "design",
  "business",
  "humanities",
  "health",
];

export type FieldScores = Record<OpportunityField, number>;

const FIELD_ZERO: FieldScores = {
  cs: 0,
  biology: 0,
  math: 0,
  physics: 0,
  engineering: 0,
  interdisciplinary: 0,
  design: 0,
  business: 0,
  humanities: 0,
  health: 0,
};

/**
 * Field-interest percentages, summing to exactly 100.
 *
 * Raw sums become shares of the total: every point an answer gives one
 * field is a point no other field gets, so the percentages are forced
 * apart by construction instead of clustering. Largest-remainder rounding
 * keeps the sum at 100 without disturbing the ranking.
 */
export function scoreFieldInterests(answers: AssessmentAnswers): FieldScores {
  const raw = { ...FIELD_ZERO };
  for (const question of assessmentQuestions) {
    const answer = answers[question.id];
    if (!answer) continue;
    const paid = contribution(question, answer);
    if (!paid?.fields) continue;
    for (const field of FIELD_KEYS) {
      raw[field] += (paid.fields[field] ?? 0) * paid.weight;
    }
  }

  const total = FIELD_KEYS.reduce((sum, field) => sum + raw[field], 0);
  if (total === 0) return raw;

  const shares = FIELD_KEYS.map((field) => ({
    field,
    share: (raw[field] / total) * 100,
  }));
  const scores = { ...FIELD_ZERO };
  for (const { field, share } of shares) scores[field] = Math.floor(share);

  let leftover = 100 - FIELD_KEYS.reduce((sum, field) => sum + scores[field], 0);
  const byRemainder = [...shares].sort(
    (a, b) => (b.share % 1) - (a.share % 1),
  );
  for (const { field } of byRemainder) {
    if (leftover <= 0) break;
    scores[field] += 1;
    leftover -= 1;
  }
  return scores;
}

/**
 * The fields the quiz says clearly lead: top two, but the runner-up only
 * counts when it holds at least half the leader's share — one dominant
 * interest should read as one, not be padded into two.
 */
export function leadingFields(scores: FieldScores): OpportunityField[] {
  const ranked = [...FIELD_KEYS]
    .filter((field) => scores[field] > 0)
    .sort((a, b) => scores[b] - scores[a]);
  if (ranked.length === 0) return [];
  const [first, second] = ranked;
  if (second && scores[second] * 2 >= scores[first]) return [first, second];
  return [first];
}

function cosine(a: number[], b: number[]): number {
  let dot = 0;
  let na = 0;
  let nb = 0;
  for (let i = 0; i < a.length; i += 1) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  if (na === 0 || nb === 0) return 0;
  return dot / (Math.sqrt(na) * Math.sqrt(nb));
}

function vector(traits: Record<TraitKey, number>): number[] {
  return TRAIT_KEYS.map((trait) => traits[trait]);
}

export type ScoredArchetype = {
  archetype: Archetype;
  /** Trait-shape closeness as a 0-99 percentage (plus any interest bonus). */
  fit: number;
  /** True when the fit includes an interest-field bonus. */
  interestAligned: boolean;
};

/**
 * Interest bonus: +4 per opportunity field shared between the archetype and
 * the student's stated interests, capped at +8 and 99 total. Cosine still
 * dominates — interests break ties and surface professions in the student's
 * own fields, they never override the trait profile.
 */
const INTEREST_BONUS_PER_FIELD = 4;
const INTEREST_BONUS_CAP = 8;

/** Onboarding interest labels → opportunity field keys. */
export const INTEREST_TO_FIELD: Record<string, OpportunityField> = {
  "Computer Science": "cs",
  Biology: "biology",
  Mathematics: "math",
  Physics: "physics",
  Engineering: "engineering",
  Interdisciplinary: "interdisciplinary",
  Design: "design",
  Business: "business",
  Humanities: "humanities",
  Health: "health",
};

export function interestFields(interests: string[]): OpportunityField[] {
  return interests
    .map((label) => INTEREST_TO_FIELD[label])
    .filter((field): field is OpportunityField => Boolean(field));
}

/** Every archetype scored against the student's trait vector, best first. */
export function rankArchetypes(
  traits: TraitScores,
  fields: OpportunityField[] = [],
): ScoredArchetype[] {
  const student = vector(traits);
  return archetypes
    .map((archetype) => {
      // Fit is the inverted root-mean-square gap between the student's
      // trait shape and the archetype's, on a shared 0-100 axis
      // (archetype traits are authored 0-10). Cosine was used before,
      // but two all-positive 6-vectors almost always cosine to 0.9+,
      // which pinned every archetype at "99% fit" — RMS distance keeps
      // the ranking honest AND the percentages spread out.
      const target = vector(archetype.traits).map((t) => t * 10);
      const gap = Math.sqrt(
        student.reduce((sum, s, i) => sum + (s - target[i]) ** 2, 0) /
          student.length,
      );
      const base = 100 - gap;
      const overlap = archetype.fields.filter((field) =>
        fields.includes(field),
      ).length;
      const bonus = Math.min(
        overlap * INTEREST_BONUS_PER_FIELD,
        INTEREST_BONUS_CAP,
      );
      return {
        archetype,
        fit: Math.min(99, Math.round(base + bonus)),
        interestAligned: bonus > 0,
      };
    })
    .sort((a, b) => b.fit - a.fit);
}

export type PathKind = "safe" | "ambitious" | "unconventional";

export type FuturePath = ScoredArchetype & {
  kind: PathKind;
  /** One line naming why this archetype landed in this slot. */
  rationale: string;
};

const PATH_LABELS: Record<PathKind, string> = {
  safe: "Safe fit",
  ambitious: "Ambitious fit",
  unconventional: "Unconventional fit",
};

export function pathLabel(kind: PathKind): string {
  return PATH_LABELS[kind];
}

/** Mean of an archetype's trait demands — how much it asks of anyone. */
function demand(archetype: Archetype): number {
  const v = vector(archetype.traits);
  return v.reduce((sum, n) => sum + n, 0) / v.length;
}

/**
 * Pick the three paths shown on /futures.
 *
 * Falls back gracefully when the archetype library is small: with fewer than
 * three archetypes the caller just gets fewer paths rather than duplicates.
 */
export function selectFuturePaths(
  traits: TraitScores,
  fields: OpportunityField[] = [],
): FuturePath[] {
  const ranked = rankArchetypes(traits, fields);
  if (ranked.length === 0) return [];

  const paths: FuturePath[] = [];
  const used = new Set<string>();

  const safe = ranked[0];
  used.add(safe.archetype.id);
  paths.push({
    ...safe,
    kind: "safe",
    rationale: safe.interestAligned
      ? `Closest match to your trait profile at ${safe.fit}% fit — and in a field you named.`
      : `Closest match to your trait profile at ${safe.fit}% fit.`,
  });

  const rest = ranked.filter((r) => !used.has(r.archetype.id));

  if (rest.length > 0) {
    // Most demanding archetype among the top half of the student's own
    // ranking — a stretch that is still plausibly theirs, so "ambitious"
    // varies by student instead of always being the most demanding
    // archetype in the library.
    const plausible = rest.slice(0, Math.max(1, Math.ceil(rest.length / 2)));
    const ambitious = plausible.reduce((best, current) =>
      demand(current.archetype) > demand(best.archetype) ? current : best,
    );
    used.add(ambitious.archetype.id);
    paths.push({
      ...ambitious,
      kind: "ambitious",
      rationale: `Still a ${ambitious.fit}% fit, but asks the most across every trait — the stretch option.`,
    });
  }

  const remaining = ranked.filter((r) => !used.has(r.archetype.id));
  if (remaining.length > 0) {
    const safeVector = vector(safe.archetype.traits);
    const unconventional = remaining.reduce((most, current) =>
      cosine(vector(current.archetype.traits), safeVector) <
      cosine(vector(most.archetype.traits), safeVector)
        ? current
        : most,
    );
    paths.push({
      ...unconventional,
      kind: "unconventional",
      rationale: `Points furthest from your safe pick — a different shape of work you may not have considered.`,
    });
  }

  return paths;
}

// ---------------------------------------------------------------------------
// Persistence
//
// Answers live in localStorage for now, read through lib/use-assessment.ts. The
// Supabase schema already has behaviour_events / latent_profiles / future_paths
// tables for the server-side version, but no backend routes expose them yet,
// and nothing has ever written a row to any of the three. Only the derived
// trait_scores / field_scores reach the server, via POST /assessment-profile.
// ---------------------------------------------------------------------------

export const STORAGE_KEY = "northstar.assessment.answers";

/**
 * Parse a stored payload into answers, dropping anything that no longer exists
 * in the question bank so an edited question cannot resurrect a stale answer.
 * Returns null for absent, malformed, or fully stale data.
 *
 * Reading and writing localStorage lives in lib/use-assessment.ts; this stays a
 * pure function so it is trivially testable and safe on the server.
 */
export function parseAnswers(raw: string | null): AssessmentAnswers | null {
  if (!raw) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== "object") return null;

  const valid: AssessmentAnswers = {};
  for (const question of assessmentQuestions) {
    const stored = (parsed as Record<string, unknown>)[question.id];
    if (typeof stored !== "string") continue;
    // contribution() already knows how to recognize a valid answer for
    // either kind, so validation and scoring can never drift apart.
    if (contribution(question, stored)) {
      valid[question.id] = stored;
    }
  }
  return Object.keys(valid).length > 0 ? valid : null;
}

export function isComplete(answers: AssessmentAnswers): boolean {
  return assessmentQuestions.every((q) => Boolean(answers[q.id]));
}
