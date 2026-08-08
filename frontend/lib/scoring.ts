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

import { assessmentQuestions, type TraitKey } from "./assessment";
import { archetypes, type Archetype } from "./archetypes";

export type TraitScores = Record<TraitKey, number>;

/** questionId → choiceId */
export type AssessmentAnswers = Record<string, string>;

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
      const best = Math.max(
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
    const chosenId = answers[question.id];
    if (!chosenId) continue;
    const choice = question.choices.find((c) => c.id === chosenId);
    if (!choice) continue;
    for (const trait of TRAIT_KEYS) {
      raw[trait] += choice.traits[trait] ?? 0;
    }
  }

  const scores = { ...ZERO };
  for (const trait of TRAIT_KEYS) {
    const ceiling = MAXIMUM[trait];
    scores[trait] = ceiling > 0 ? Math.round((raw[trait] / ceiling) * 100) : 0;
  }
  return scores;
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
  /** Cosine similarity as a 0-100 percentage. */
  fit: number;
};

/** Every archetype scored against the student's trait vector, best first. */
export function rankArchetypes(traits: TraitScores): ScoredArchetype[] {
  const student = vector(traits);
  return archetypes
    .map((archetype) => ({
      archetype,
      fit: Math.round(cosine(student, vector(archetype.traits)) * 100),
    }))
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
export function selectFuturePaths(traits: TraitScores): FuturePath[] {
  const ranked = rankArchetypes(traits);
  if (ranked.length === 0) return [];

  const paths: FuturePath[] = [];
  const used = new Set<string>();

  const safe = ranked[0];
  used.add(safe.archetype.id);
  paths.push({
    ...safe,
    kind: "safe",
    rationale: `Closest match to your trait profile at ${safe.fit}% fit.`,
  });

  const rest = ranked.filter((r) => !used.has(r.archetype.id));

  if (rest.length > 0) {
    const ambitious = rest.reduce((best, current) =>
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
// tables for the server-side version, but no backend routes expose them yet —
// see docs/TASK_SPLIT.md.
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
    const choiceId = (parsed as Record<string, unknown>)[question.id];
    if (
      typeof choiceId === "string" &&
      question.choices.some((c) => c.id === choiceId)
    ) {
      valid[question.id] = choiceId;
    }
  }
  return Object.keys(valid).length > 0 ? valid : null;
}

export function isComplete(answers: AssessmentAnswers): boolean {
  return assessmentQuestions.every((q) => Boolean(answers[q.id]));
}
