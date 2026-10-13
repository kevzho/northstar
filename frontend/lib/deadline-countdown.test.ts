/**
 * The day count on the landing page ticker.
 *
 * This bug has now happened twice in this codebase, in two files, for the same
 * reason: measuring a REMAINING DURATION in milliseconds and then labelling the
 * result a day count. lib/pathways.ts#whenLabel had it and was fixed; this copy
 * in CatalogSignals was missed, so every deadline on the landing page read one
 * day further away than it was, and something closing tonight said "1d".
 *
 * A deadline count is calendar arithmetic, not duration arithmetic. These cases
 * are written from the clock time that exposed it.
 */

import { describe, expect, it } from "vitest";
import { daysUntil } from "./countdown";

const at = (iso: string) => new Date(iso).getTime();

describe("daysUntil", () => {
  it("calls a deadline today zero, at any hour", () => {
    // 22:00 was the failing case: two hours of duration left, ceil() -> 1.
    expect(daysUntil("2026-10-12", at("2026-10-12T22:00:00"))).toBe(0);
    expect(daysUntil("2026-10-12", at("2026-10-12T00:05:00"))).toBe(0);
    expect(daysUntil("2026-10-12", at("2026-10-12T12:00:00"))).toBe(0);
  });

  it("calls tomorrow one, not two", () => {
    expect(daysUntil("2026-10-13", at("2026-10-12T22:00:00"))).toBe(1);
    expect(daysUntil("2026-10-13", at("2026-10-12T01:00:00"))).toBe(1);
  });

  it("counts whole calendar days out to a week", () => {
    expect(daysUntil("2026-10-14", at("2026-10-12T22:00:00"))).toBe(2);
    expect(daysUntil("2026-10-19", at("2026-10-12T22:00:00"))).toBe(7);
  });

  it("goes negative once the date has passed, so 'today' is not sticky", () => {
    expect(daysUntil("2026-10-11", at("2026-10-12T09:00:00"))).toBe(-1);
  });

  it("survives a DST boundary", () => {
    // US DST ends 2026-11-01. Both sides are anchored at local noon so the
    // extra hour cannot shift a date across midnight.
    expect(daysUntil("2026-11-02", at("2026-10-31T23:30:00"))).toBe(2);
    expect(daysUntil("2026-11-01", at("2026-10-31T23:30:00"))).toBe(1);
  });

  it("agrees with the Congressional App Challenge's own date", () => {
    // The row this project is submitted to. It said 2026-10-24 until a stress
    // test caught it; the real close is 2026-10-26, 12:00 PM ET.
    expect(daysUntil("2026-10-26", at("2026-10-12T22:00:00"))).toBe(14);
  });
});
