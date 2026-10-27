/**
 * Guard: a sticky bar that paints a background must paint it edge to edge.
 *
 * The landing page's nav lives inside the centred `max-w-6xl` column and
 * carried `bg-background/80`, so its background was painted to the column's
 * width, not the viewport's. For most of the page that is invisible, the bar
 * and the page behind it are the same colour, so nobody can see where one stops
 * and the other starts.
 *
 * Then the bar scrolls over `.panel-paper.bleed-x`, the full-bleed paper band
 * near the foot of the page, and it stops being invisible: a dark rectangle
 * floating in the middle of the viewport with paper either side of it, the
 * border-bottom stopping dead a couple of hundred pixels short of each edge.
 * It shipped because the only way to see it is to scroll to one specific
 * section of one page in either theme.
 *
 * The fix is `.bleed-bg` in globals.css, which bleeds a pseudo-element instead
 * of the bar. `.bleed-x` cannot be used here: it sets `position: relative`,
 * which would cancel the `position: sticky` that makes the bar a bar.
 *
 * The rule: if a className is sticky AND paints a background, it must say how
 * far that background reaches. Today exactly one element in the codebase is
 * sticky, so this costs nothing until someone adds the second one.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = join(__dirname, "..");

function tsxFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry.startsWith(".")) continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...tsxFiles(full));
    else if (full.endsWith(".tsx")) out.push(full);
  }
  return out;
}

describe("sticky bars", () => {
  it("paint their background across the viewport, not the column", () => {
    const offenders: string[] = [];

    for (const file of [...tsxFiles(join(ROOT, "app")), ...tsxFiles(join(ROOT, "components"))]) {
      const src = readFileSync(file, "utf8");
      for (const m of src.matchAll(/className="([^"]*)"/g)) {
        const cls = m[1];
        if (!/\bsticky\b/.test(cls)) continue;
        // Only a bar that PAINTS can show the seam. A transparent sticky
        // element has no background to stop short.
        if (!/\bbg-[a-z]/.test(cls) && !/\bbleed-bg\b/.test(cls)) continue;
        // Either it bleeds, or it is already full-width in its own right.
        const handled =
          /\bbleed-bg\b/.test(cls) || /\binset-x-0\b/.test(cls) || /\bw-screen\b/.test(cls);
        if (!handled) {
          offenders.push(`${file.replace(ROOT, "")}: ${cls}`);
        }
      }
    }

    expect(
      offenders,
      "a sticky element paints a background but never says how wide: it will " +
        "stop at the column edge and show a seam over any full-bleed band. " +
        "Add `bleed-bg` (see app/globals.css) or make it full-width.",
    ).toEqual([]);
  });

  it("has the bleed-bg utility it depends on", () => {
    // A className referencing a class nobody defines is a silent no-op, which
    // would make the guard above pass while the seam came back.
    const css = readFileSync(join(ROOT, "app", "globals.css"), "utf8");
    expect(css).toContain(".bleed-bg::before");
    expect(css).toMatch(/\.bleed-bg::before\s*\{[^}]*width:\s*100vw/);
  });
});
