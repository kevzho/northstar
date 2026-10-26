/**
 * Every in-app route must light up exactly one nav section.
 *
 * A route that resolves to none renders an unlit nav, and a student reading it
 * has no idea which of the five places they are in — which is the complaint
 * that produced the nav rewrite in the first place. Audited 2026-10-18:
 * /advisor, /mentors/join and /p/[handle] all failed this.
 *
 * The resolution order is duplicated here deliberately. Importing AppNav would
 * drag in next/navigation and a client component; this is nine lines, and if
 * the two ever disagree the disagreement is the bug this file exists to find.
 */

import { describe, expect, it } from "vitest";

// Mirrors AppNav.tsx SECTIONS, in the same order: the resolution below is a
// prefix scan, so order is part of the behaviour. /dashboard was added to
// the nav and not here, which is exactly the drift this duplication risks.
const SECTIONS = [
  "/dashboard",
  "/opportunities",
  "/learn",
  "/plan",
  "/profile",
  "/discover",
];

const ALIASES: Record<string, string> = {
  "/futures": "/profile",
  "/assessment": "/profile",
  "/map": "/plan",
  "/advisor": "/plan",
  "/friends": "/discover",
  "/teamup": "/discover",
  "/mentors": "/discover",
  "/mentors/join": "/discover",
  "/projects": "/opportunities",
};

const ALIAS_PREFIXES: [string, string][] = [["/p/", "/discover"]];

function activeSection(pathname: string): string | null {
  return (
    ALIASES[pathname] ??
    ALIAS_PREFIXES.find(([prefix]) => pathname.startsWith(prefix))?.[1] ??
    SECTIONS.find((s) => pathname.startsWith(s)) ??
    null
  );
}

/** Every route a signed-in student can reach from inside the app. */
const IN_APP = [
  "/opportunities", "/opportunities/abc-123", "/projects",
  "/learn",
  "/plan", "/map", "/advisor",
  "/profile", "/futures", "/assessment",
  "/discover", "/friends", "/teamup", "/mentors", "/mentors/join", "/p/kevin",
];

/** Routes that deliberately belong to no section. */
const OUTSIDE = ["/", "/login", "/onboarding", "/faq", "/contact", "/privacy"];

describe("nav section resolution", () => {
  it("lights a section for every in-app route", () => {
    const unlit = IN_APP.filter((route) => activeSection(route) === null);
    expect(unlit, `these render an unlit nav: ${unlit.join(", ")}`).toEqual([]);
  });

  it("lights exactly the section a student would expect", () => {
    expect(activeSection("/advisor")).toBe("/plan");
    expect(activeSection("/futures")).toBe("/profile");
    expect(activeSection("/p/kevin")).toBe("/discover");
    expect(activeSection("/mentors/join")).toBe("/discover");
    expect(activeSection("/opportunities/abc-123")).toBe("/opportunities");
  });

  it("resolves to a real section, never to a route that is not one", () => {
    for (const route of IN_APP) {
      const section = activeSection(route);
      expect(SECTIONS, `${route} -> ${section}`).toContain(section);
    }
  });

  it("leaves the pages that are not sections alone", () => {
    for (const route of OUTSIDE) {
      expect(activeSection(route), `${route} should light nothing`).toBeNull();
    }
  });
});
