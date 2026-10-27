/**
 * Guard: the text alternative orders matches the same way the picture does.
 *
 * components/PathwayMap.tsx states that the SVG is "decorative and mouse-only", so for a
 * keyboard or screen-reader user the list is not a convenience, it is the only
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

describe("the map's accessibility contract", () => {
  // Repointed when /map became a section of /plan. The read is at describe
  // scope, so a stale path throws during COLLECTION and takes the six
  // ordering tests above it down with it -- the failure would read as
  // "pathways are broken" rather than "a file moved".
  const src = readFileSync(
    join(__dirname, "..", "components", "PathwayMap.tsx"),
    "utf8",
  );

  it("hides the decorative svg from assistive technology", () => {
    // Exposed, it is several hundred unlabelled shapes with no meaning.
    //
    // Checked as a RELATIONSHIP, not as a formatting shape. This assertion
    // used to be /aria-hidden="true"\s*>\s*\n\s*<svg/, which broke the day a
    // className was added to the wrapper -- the markup was still correct and
    // the test still failed. A guard that fires on whitespace tells you
    // nothing about accessibility.
    const wrapper = src.lastIndexOf('aria-hidden="true"', src.indexOf("<svg ref={svgRef}"));
    expect(wrapper, "no aria-hidden ancestor before the svg").toBeGreaterThan(-1);
    const between = src.slice(wrapper, src.indexOf("<svg ref={svgRef}"));
    expect(between, "the aria-hidden element closes before the svg").not.toContain("</div>");
  });

  it("still offers the list that replaces it", () => {
    expect(src).toContain("<PathwayList");
    expect(src).toMatch(/aria-pressed=\{view === value\}/);
  });

  it("does not swallow the page's scroll", () => {
    // The map used to own a short route, so d3.zoom on the whole svg plus
    // touch-action:none was fine. It now sits mid-scroll above the step list:
    // a wheel that zooms instead of scrolling, or a touch surface that eats a
    // swipe, strands a student above the part of the page with the
    // instructions in it.
    expect(src).not.toMatch(/touch-action", "none"/);
    expect(src).toMatch(/touch-action", "pan-y"/);
    expect(src).toMatch(/event\.ctrlKey \|\| event\.metaKey/);
  });

  it("bounds its own height rather than trusting CSS to", () => {
    // A fixed-aspect viewBox at width:100% takes its height from the column
    // width and the row count; max-height can only crop it. Ten fields would
    // drop ~2800px of diagram between the roadmap tree and the step list.
    expect(src).toContain("MAX_SYSTEMS");
    expect(src).toMatch(/slice\(0, MAX_SYSTEMS\)/);
  });

  it("says what it left out instead of silently truncating", () => {
    expect(src).toContain("hiddenFields");
  });

  it("does not gate auth a second time", () => {
    // The host page owns the gate; two calls race two router.replace calls.
    // Matched on the CALL, not the word: the component's own comment explains
    // why the hook is absent, and a substring check would fail on the
    // explanation. That is the same way a guard in test_impact_claims.py once
    // matched its own docstring.
    expect(src).not.toMatch(/useRequireAuth\s*\(/);
    expect(src).toContain("no useRequireAuth here");
  });
});

describe("the map's rendered height, which CSS cannot cap", () => {
  // The svg is a fixed-aspect viewBox at width:100%, so its height is
  // column-width x (rows*CELL_H)/(cols*CELL_W). max-height can only crop it
  // and min-height only pads it, neither changes the number below. This was
  // the hazard an inventory pass called "guaranteed, on camera, and invisible
  // in a dev window with a short match list": a 10-field student dropped
  // ~2300px of diagram between the roadmap tree and the step list.
  const CELL_W = 620;
  const CELL_H = 560;
  const COLUMN_PX = 1024; // /plan is max-w-5xl

  function renderedHeight(systems: number): number {
    const cols = systems <= 1 ? 1 : 2;
    const rows = Math.ceil(systems / cols);
    return Math.round((COLUMN_PX * (rows * CELL_H)) / (cols * CELL_W));
  }

  it("is bounded for every profile once the system count is capped", () => {
    const MAX_SYSTEMS = 4;
    for (const fields of [1, 2, 3, 5, 8, 10, 14]) {
      const capped = renderedHeight(Math.min(fields, MAX_SYSTEMS));
      expect(capped, `${fields} fields renders ${capped}px`).toBeLessThanOrEqual(1000);
    }
  });

  it("would be unbounded without the cap, which is why the cap exists", () => {
    expect(renderedHeight(10)).toBeGreaterThan(2000);
    expect(renderedHeight(14)).toBeGreaterThan(3000);
  });

  it("uses the same cap the component does", () => {
    const src = readFileSync(
      join(__dirname, "..", "components", "PathwayMap.tsx"),
      "utf8",
    );
    const declared = /const MAX_SYSTEMS = (\d+)/.exec(src);
    expect(declared, "MAX_SYSTEMS is gone from the component").not.toBeNull();
    expect(renderedHeight(Number(declared![1]))).toBeLessThanOrEqual(1000);
  });
});
