/**
 * Guard: the text alternative orders matches the same way the picture does.
 *
 * app/map/page.tsx states that the SVG is "decorative and mouse-only", so for a
 * keyboard or screen-reader user the list is not a convenience — it is the only
 * way to use the page. That makes its ordering load-bearing: the map's entire
 * claim is that distance from the star means urgency, and if the list sorts
 * differently it quietly tells a different student a different thing is next.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { daysOut, groupByField, whenLabel, type PathwayNode } from "./pathways";

const NOW = new Date("2026-10-03T12:00:00Z").getTime();

function node(over: Partial<PathwayNode> & { id: string }): PathwayNode {
  return {
    title: over.id, field: "cs", type: "competition", score: 1, tags: [], ...over,
  };
}

describe("pathway ordering", () => {
  it("puts the soonest deadline first and rolling last", () => {
    const [{ items }] = groupByField(
      [
        node({ id: "rolling", deadline: null }),
        node({ id: "far", deadline: "2026-12-01" }),
        node({ id: "soon", deadline: "2026-10-10" }),
      ],
      NOW,
    );
    expect(items.map((i) => i.id)).toEqual(["soon", "far", "rolling"]);
  });

  it("orders fields by how many matches they hold", () => {
    const groups = groupByField(
      [
        node({ id: "a", field: "math" }),
        node({ id: "b", field: "cs" }),
        node({ id: "c", field: "cs" }),
      ],
      NOW,
    );
    expect(groups.map((g) => g.field)).toEqual(["cs", "math"]);
  });

  it("files an empty field under interdisciplinary, as the map does", () => {
    expect(groupByField([node({ id: "a", field: "" })], NOW)[0].field).toBe(
      "interdisciplinary",
    );
  });

  it("keeps every match, unlike the eight the map can draw", () => {
    // The cap is a property of a fixed-size cell, not of the data. A keyboard
    // user losing their ninth-most-urgent match is the bug this file prevents.
    const many = Array.from({ length: 12 }, (_, i) =>
      node({ id: `n${i}`, deadline: `2026-11-${String(i + 1).padStart(2, "0")}` }),
    );
    expect(groupByField(many, NOW)[0].items).toHaveLength(12);
  });

  it("treats a malformed deadline as rolling rather than crashing", () => {
    expect(daysOut("not-a-date", NOW)).toBe(9999);
    expect(whenLabel("not-a-date", NOW)).toBe("Rolling deadline");
  });

  it("says the urgency in words, not just a date", () => {
    expect(whenLabel(null, NOW)).toBe("Rolling deadline");
    expect(whenLabel("2026-10-03", NOW)).toMatch(/^Closes today/);
    expect(whenLabel("2026-10-04", NOW)).toMatch(/^Closes tomorrow/);
    expect(whenLabel("2026-10-13", NOW)).toMatch(/^Closes in 10 days/);
  });
});

describe("the map page's accessibility contract", () => {
  const src = readFileSync(join(__dirname, "..", "app", "map", "page.tsx"), "utf8");

  it("hides the decorative svg from assistive technology", () => {
    // Exposed, it is several hundred unlabelled shapes with no meaning.
    expect(src).toMatch(/aria-hidden="true"\s*>\s*\n\s*<svg/);
  });

  it("still offers the list that replaces it", () => {
    expect(src).toContain("<PathwayList");
    expect(src).toMatch(/aria-pressed=\{view === value\}/);
  });
});
