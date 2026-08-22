/**
 * Invariant tests for the scoring engine — the code a judge will ask about.
 *
 * These pin properties, not constants (same philosophy as the backend's
 * test_match.py): trait scores stay in bounds, field shares always sum to
 * 100, the three future paths are distinct, and stale answers can't leak
 * through parseAnswers. Tuning weights in assessment.ts must not break
 * this file; changing the *rules* should.
 */

import { describe, expect, it } from "vitest";
import {
  LIKERT_VALUES,
  assessmentQuestions,
  type LikertValue,
} from "./assessment";
import {
  FIELD_KEYS,
  TRAIT_KEYS,
  isComplete,
  leadingFields,
  parseAnswers,
  rankArchetypes,
  scoreFieldInterests,
  scoreTraits,
  selectFuturePaths,
  type AssessmentAnswers,
} from "./scoring";

/**
 * Every question answered: picks take their option at `index` (wrapping),
 * rating questions all take `rating`.
 */
function answersByIndex(
  index: number,
  rating: LikertValue = 4,
): AssessmentAnswers {
  const answers: AssessmentAnswers = {};
  for (const question of assessmentQuestions) {
    answers[question.id] =
      question.kind === "likert"
        ? String(rating)
        : question.choices[index % question.choices.length].id;
  }
  return answers;
}

/**
 * Picks that all point at CS, with every rating question at "Strongly
 * disagree" so the non-CS interest statements pay out nothing — CS should
 * then lead by a wide margin.
 */
const CS_LEANING: AssessmentAnswers = {
  ...answersByIndex(0, 1),
  "q4-headline": "ai-diagnosis",
  "q5-fun-class": "ethics-of-tech",
  "q6-career-day": "game-engineer",
};

describe("scoreTraits", () => {
  it("keeps every trait in [0, 100] at every rating", () => {
    for (const rating of LIKERT_VALUES) {
      for (const index of [0, 1, 2, 3, 4]) {
        const scores = scoreTraits(answersByIndex(index, rating));
        for (const trait of TRAIT_KEYS) {
          expect(scores[trait]).toBeGreaterThanOrEqual(0);
          expect(scores[trait]).toBeLessThanOrEqual(100);
        }
      }
    }
  });

  it("scores an empty answer set as all zeros", () => {
    const scores = scoreTraits({});
    for (const trait of TRAIT_KEYS) expect(scores[trait]).toBe(0);
  });
});

describe("scoreFieldInterests", () => {
  it("always sums to exactly 100 for complete answers", () => {
    for (const rating of LIKERT_VALUES) {
      for (const index of [0, 1, 2, 3, 4]) {
        const scores = scoreFieldInterests(answersByIndex(index, rating));
        const total = FIELD_KEYS.reduce((sum, field) => sum + scores[field], 0);
        expect(total).toBe(100);
      }
    }
  });

  it("stays at 100 for a mixed run (some ratings, some picks)", () => {
    for (const index of [0, 1, 2]) {
      const scores = scoreFieldInterests(answersByIndex(index));
      const total = FIELD_KEYS.reduce((sum, field) => sum + scores[field], 0);
      expect(total).toBe(100);
    }
  });

  it("ranks the field the answers lean toward first", () => {
    const scores = scoreFieldInterests(CS_LEANING);
    const top = [...FIELD_KEYS].sort((a, b) => scores[b] - scores[a])[0];
    expect(top).toBe("cs");
    expect(scores.cs).toBeGreaterThan(30); // clearly distinct, not mush
  });

  it("returns all zeros when no field-signal questions are answered", () => {
    const scores = scoreFieldInterests({ "q1-free-afternoon": "build-project" });
    for (const field of FIELD_KEYS) expect(scores[field]).toBe(0);
  });
});

describe("leadingFields", () => {
  it("collapses to one field when the leader dominates", () => {
    const leading = leadingFields({
      cs: 80, biology: 10, math: 10, physics: 0, engineering: 0, interdisciplinary: 0, design: 0, business: 0, humanities: 0, health: 0,
    });
    expect(leading).toEqual(["cs"]);
  });

  it("keeps a genuine runner-up (at least half the leader)", () => {
    const leading = leadingFields({
      cs: 40, biology: 30, math: 30, physics: 0, engineering: 0, interdisciplinary: 0, design: 0, business: 0, humanities: 0, health: 0,
    });
    expect(leading).toHaveLength(2);
    expect(leading[0]).toBe("cs");
  });

  it("returns nothing for an all-zero distribution", () => {
    expect(
      leadingFields({
        cs: 0, biology: 0, math: 0, physics: 0, engineering: 0, interdisciplinary: 0, design: 0, business: 0, humanities: 0, health: 0,
      }),
    ).toEqual([]);
  });
});

describe("selectFuturePaths", () => {
  const traits = scoreTraits(CS_LEANING);

  it("returns three distinct kinds over three distinct archetypes", () => {
    const paths = selectFuturePaths(traits);
    expect(paths.map((p) => p.kind)).toEqual([
      "safe",
      "ambitious",
      "unconventional",
    ]);
    const ids = paths.map((p) => p.archetype.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("puts the top-ranked archetype in the safe slot", () => {
    const [best] = rankArchetypes(traits);
    const safe = selectFuturePaths(traits).find((p) => p.kind === "safe");
    expect(safe?.archetype.id).toBe(best.archetype.id);
  });

  it("interest fields can only raise a fit, never lower it", () => {
    const plain = rankArchetypes(traits);
    const boosted = rankArchetypes(traits, ["cs"]);
    for (const scored of boosted) {
      const before = plain.find(
        (p) => p.archetype.id === scored.archetype.id,
      );
      expect(scored.fit).toBeGreaterThanOrEqual(before!.fit);
    }
  });
});

describe("the 1-5 rating scale", () => {
  const likert = assessmentQuestions.filter((q) => q.kind === "likert");
  const picks = assessmentQuestions.filter((q) => q.kind === "choice");

  it("mixes both formats, and no pick is down to three options", () => {
    expect(likert.length).toBeGreaterThan(0);
    expect(picks.length).toBeGreaterThan(0);
    for (const question of picks) {
      // Three was too few to describe a real student; four is the floor.
      expect(question.choices.length).toBeGreaterThanOrEqual(4);
    }
  });

  it("pays a forward item more the more you agree", () => {
    const base = answersByIndex(0, 3);
    const agree = scoreTraits({ ...base, "l3-long-odds": "5" });
    const disagree = scoreTraits({ ...base, "l3-long-odds": "1" });
    expect(agree.riskTolerance).toBeGreaterThan(disagree.riskTolerance);
  });

  it("pays a reverse-coded item more the more you disagree", () => {
    const base = answersByIndex(0, 3);
    const agree = scoreTraits({ ...base, "l4-need-instructions": "5" });
    const disagree = scoreTraits({ ...base, "l4-need-instructions": "1" });
    expect(disagree.ambiguityComfort).toBeGreaterThan(agree.ambiguityComfort);
  });

  it("is monotonic across the whole scale", () => {
    const base = answersByIndex(0, 3);
    const scores = LIKERT_VALUES.map(
      (v) => scoreTraits({ ...base, "l3-long-odds": String(v) }).riskTolerance,
    );
    for (let i = 1; i < scores.length; i += 1) {
      expect(scores[i]).toBeGreaterThanOrEqual(scores[i - 1]);
    }
  });

  it("treats a neutral run as strictly between disagreeing and agreeing", () => {
    const low = scoreTraits(answersByIndex(0, 1));
    const mid = scoreTraits(answersByIndex(0, 3));
    const high = scoreTraits(answersByIndex(0, 5));
    // riskTolerance has no reverse-coded item, so the ordering is clean.
    expect(mid.riskTolerance).toBeGreaterThan(low.riskTolerance);
    expect(high.riskTolerance).toBeGreaterThan(mid.riskTolerance);
  });

  it("accepts only 1-5 as a stored rating", () => {
    for (const raw of ["1", "3", "5"]) {
      expect(parseAnswers(JSON.stringify({ "l3-long-odds": raw }))).toEqual({
        "l3-long-odds": raw,
      });
    }
    for (const raw of ["0", "6", "", "4.5", "agree", "take-shot"]) {
      expect(parseAnswers(JSON.stringify({ "l3-long-odds": raw }))).toBeNull();
    }
  });
});

describe("parseAnswers", () => {
  it("drops answers whose question or choice no longer exists", () => {
    const stored = JSON.stringify({
      "q1-free-afternoon": "build-project",
      "q1-free-afternoon-old": "gone",
      "q2-competition-choice": "choice-that-never-existed",
    });
    expect(parseAnswers(stored)).toEqual({
      "q1-free-afternoon": "build-project",
    });
  });

  it("returns null for malformed or fully stale payloads", () => {
    expect(parseAnswers("not json")).toBeNull();
    expect(parseAnswers(JSON.stringify({ ghost: "x" }))).toBeNull();
    expect(parseAnswers(null)).toBeNull();
  });

  it("isComplete demands an answer for every question in the bank", () => {
    expect(isComplete(answersByIndex(0))).toBe(true);
    const partial = answersByIndex(0);
    delete partial[assessmentQuestions[0].id];
    expect(isComplete(partial)).toBe(false);
  });
});
