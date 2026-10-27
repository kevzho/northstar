/**
 * Guard: number-words in shipped copy must match the real bank.
 *
 * The landing page said "Seventeen prompts", the dashboard said "Fourteen
 * prompts", /futures said "eight-question assessment" and /profile explained
 * its own scoring math "across all seventeen questions", while
 * lib/assessment.ts held 20 the whole time and /assessment rendered "Twenty
 * prompts" one click away. Three different wrong numbers, none of which any
 * test could see, because the copy spells the count as a word.
 *
 * The rule: a count-word describing the bank must equal the bank. The one
 * legitimate exception is a line that breaks the bank into parts, the
 * assessment page's "nine reveal how you build ... eleven reveal which
 * fields", so a line is allowed when its own counts sum to the total.
 * Anything else fails.
 */

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { assessmentQuestions } from "./assessment";

const ROOT = join(__dirname, "..");
const SCAN = ["app", "components", "lib"];

// "one" is deliberately absent: in this codebase it is always singular usage
// ("pick-one questions", "what one answer pays out"), never a claim that the
// bank holds one item.
const WORDS: Record<string, number> = {
  two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8,
  nine: 9, ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14,
  fifteen: 15, sixteen: 16, seventeen: 17, eighteen: 18, nineteen: 19,
  twenty: 20, thirty: 30, forty: 40, fifty: 50,
};

/** "Twenty prompts", "twenty-question assessment", "all twenty questions". */
const COUNTED = new RegExp(
  `\\b(${Object.keys(WORDS).join("|")})[- ](?:behavioral )?(prompts?|questions?|answers?|scenarios?|assessment)\\b`,
  "gi",
);
/** Bare "nine reveal ... eleven reveal", the split form with no noun. */
const BARE = new RegExp(`\\b(${Object.keys(WORDS).join("|")})\\b`, "gi");

function sources(dir: string): string[] {
  const out: string[] = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...sources(p));
    else if (/\.tsx?$/.test(name) && !name.endsWith(".test.ts")) out.push(p);
  }
  return out;
}

const TOTAL = assessmentQuestions.length;

function offenders(dir: string): string[] {
  const wrong: string[] = [];
  for (const file of sources(join(ROOT, dir))) {
    readFileSync(file, "utf8").split("\n").forEach((line, i) => {
      const hits = [...line.matchAll(COUNTED)];
      if (!hits.length) return;
      // A line that decomposes the bank is fine when its parts add up.
      const onLine = [...line.matchAll(BARE)].map((m) => WORDS[m[1].toLowerCase()]);
      const sum = onLine.reduce((a, b) => a + b, 0);
      if (onLine.length > 1 && (sum === TOTAL || sum - TOTAL === TOTAL)) return;
      for (const m of hits) {
        const stated = WORDS[m[1].toLowerCase()];
        if (stated !== TOTAL) {
          wrong.push(
            `${file.replace(ROOT + "/", "")}:${i + 1}: "${m[0]}" — the bank has ${TOTAL}`,
          );
        }
      }
    });
  }
  return wrong;
}

describe("copy counts match the assessment bank", () => {
  it("has a bank to compare against", () => {
    expect(TOTAL).toBe(20);
  });

  it.each(SCAN)("%s/ states no stale count", (dir) => {
    expect(offenders(dir).join("\n")).toBe("");
  });

  it("the split on /assessment still sums to the bank", () => {
    const page = readFileSync(join(ROOT, "app/assessment/page.tsx"), "utf8");
    const split = page.match(/nine[\s\S]{0,120}?eleven/i);
    expect(split, "the nine/eleven split copy moved or changed").not.toBeNull();
    expect(9 + 11).toBe(TOTAL);
  });
});

/**
 * The judge-facing script counts too, and nothing was checking it.
 *
 * docs/DEMO_SCRIPT.md is read aloud on camera for the Congressional App
 * Challenge, and its "numbers you can defend" table said "Six traits, eight
 * questions" while the bank held twenty. That is the identical drift the test
 * above exists to catch, it just scans app/, components/ and lib/, which are
 * .tsx and .ts, and a Markdown file in docs/ was outside it.
 *
 * A wrong number in shipped copy is a bug. A wrong number said out loud to a
 * judge is the same bug with a worse audience, so it gets the same guard.
 */
describe("the demo script", () => {
  const SCRIPT = join(ROOT, "..", "docs", "DEMO_SCRIPT.md");

  it("never spells a catalog size as a word", () => {
    // A third stale number was found by hand on 2026-10-07: "Thirty-five
    // curated STEM programs" against a shelf of 156. The guard below only
    // matches number-words before questions/prompts, so it sailed past.
    //
    // A catalog count cannot be checked against anything here, this file has
    // no database, and it changes every single day the scraper runs. So the
    // rule is simply that the script must not spell one as a word: write the
    // digits, next to the date they were counted, and re-count before
    // recording. backend/scripts/check_impact_claims.py is what verifies a
    // number against production.
    if (!existsSync(SCRIPT)) return;
    const text = readFileSync(SCRIPT, "utf8");
    const CATALOG_NOUNS =
      /\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)(?:[- ][\w-]+){0,3}[- ](opportunit\w+|programs?|programmes?|listings?|rows?|hosts?|fields?)\b/gi;
    const wrong: string[] = [];
    text.split("\n").forEach((line, i) => {
      for (const hit of line.matchAll(CATALOG_NOUNS)) {
        wrong.push(`DEMO_SCRIPT.md:${i + 1} spells a catalog size: "${hit[0]}"`);
      }
    });
    expect(
      wrong,
      "catalog sizes change daily — write digits and the date you counted them",
    ).toEqual([]);
  });

  it("states the real size of the assessment bank", () => {
    // docs/ is gitignored, so the script exists on the author's machine and not
    // in CI. Skipping where it is absent keeps the guard useful exactly where it
    // matters -- on the machine the recording is made from -- without failing a
    // build for a file the repo does not carry.
    if (!existsSync(SCRIPT)) return;
    const text = readFileSync(SCRIPT, "utf8");
    const wrong: string[] = [];
    text.split("\n").forEach((line, i) => {
      for (const hit of line.matchAll(COUNTED)) {
        const claimed = WORDS[hit[1].toLowerCase()];
        if (claimed !== TOTAL) {
          wrong.push(`DEMO_SCRIPT.md:${i + 1} says "${hit[0]}" but the bank holds ${TOTAL}`);
        }
      }
    });
    expect(wrong, "a number in the script you read to a judge is wrong").toEqual([]);
  });
});
