/**
 * Guard: every archetype must have an authored spine.
 *
 * `generatePlan` falls back to FALLBACK_SPINE for any archetype missing from
 * SPINES. For five weeks that meant 12 of 24 archetypes, half of all students -
 * received generic advice while the product presented it as a personalised
 * plan, and nothing failed. A silent fallback is the worst shape for this bug:
 * the page renders, the copy reads fine, and only a student on one of the
 * twelve ever finds out.
 *
 * skillKey joins the spine to public.learning_resources.skill_key, so a missing
 * or duplicated key means a student is shown no resources, or another path's.
 */

import { describe, expect, it } from "vitest";
import { archetypes } from "./archetypes";
import { SPINE_KEYS, spineFor, skillKeyFor } from "./plan";

describe("every archetype has an authored spine", () => {
  it("covers all 24 archetypes", () => {
    const missing = archetypes.map((a) => a.id).filter((id) => !SPINE_KEYS.includes(id));
    expect(missing, "archetypes falling through to FALLBACK_SPINE").toEqual([]);
  });

  it("gives every archetype a distinct skillKey", () => {
    const keys = archetypes.map((a) => skillKeyFor(a.id));
    expect(keys.filter((k) => !k), "archetypes with no skillKey").toEqual([]);
    const dupes = keys.filter((k, i) => keys.indexOf(k) !== i);
    expect(dupes, "two archetypes sharing a skillKey would cross-serve resources").toEqual([]);
  });

  it("gives every spine all three rungs, non-empty", () => {
    for (const a of archetypes) {
      const spine = spineFor(a.id);
      expect(spine, `no spine for ${a.id}`).toBeTruthy();
      for (const rung of ["project", "publish", "skill"] as const) {
        expect(
          (spine?.[rung] ?? "").trim().length,
          `${a.id}.${rung} is empty`,
        ).toBeGreaterThan(20);
      }
    }
  });
});
