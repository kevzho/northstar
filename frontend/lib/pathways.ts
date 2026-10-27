/**
 * Ordering shared by the pathway map and its text alternative.
 *
 * The map draws urgency as distance from a star; the list draws it as position
 * in an ordered list. Those are the same claim, so they must come from the same
 * sort, if they drift, the alternative stops being equivalent and starts being
 * a second, quieter opinion about what is urgent.
 *
 * Pure and DOM-free so it can be tested directly, the way lib/scoring.ts is.
 */

export type PathwayNode = {
  id: string;
  title: string;
  field: string;
  type: string;
  score: number;
  deadline?: string | null;
  tags: string[];
};

/**
 * Days until a deadline. Rolling and malformed both sort last, which is what
 * puts them on the outermost orbit in the picture.
 */
export function daysOut(deadline: string | null | undefined, now = Date.now()): number {
  if (!deadline) return 9999;
  const t = new Date(`${deadline}T23:59:59`).getTime();
  if (Number.isNaN(t)) return 9999;
  return Math.max(0, (t - now) / 86_400_000);
}

/**
 * One group per field, each sorted soonest-deadline-first, groups ordered by
 * size, the same three rules the SVG uses to lay out its solar systems.
 *
 * Note what is absent: the map's `.slice(0, 8)`. A ninth planet has nowhere to
 * go in a fixed cell, but a list has room, and dropping a student's ninth-most
 * urgent match from the only view they can operate would defeat the point.
 */
export function groupByField(nodes: PathwayNode[], now = Date.now()) {
  const byField = new Map<string, PathwayNode[]>();
  for (const node of nodes) {
    const field = node.field || "interdisciplinary";
    byField.set(field, [...(byField.get(field) ?? []), node]);
  }
  return [...byField.entries()]
    .map(([field, items]) => ({
      field,
      items: [...items].sort(
        (a, b) => daysOut(a.deadline, now) - daysOut(b.deadline, now),
      ),
    }))
    .sort((a, b) => b.items.length - a.items.length);
}

/**
 * The urgency an orbit radius shows, said in words.
 *
 * Counts CALENDAR days, not elapsed hours. `daysOut` is deliberately
 * fractional, because sorting wants the finer signal, but rounding that
 * fraction for a label is wrong in a way that reads as a lie: a deadline at
 * 23:59 tonight is 0.8 days away at lunchtime, which rounds to 1, and the page
 * tells a student "Closes tomorrow" about something that closes tonight. On a
 * view whose only job is urgency, that is the one error worth never making.
 */
export function whenLabel(deadline: string | null | undefined, now = Date.now()): string {
  if (!deadline) return "Rolling deadline";
  const end = new Date(`${deadline}T23:59:59`);
  if (Number.isNaN(end.getTime())) return "Rolling deadline";

  const midnight = (d: Date) =>
    new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  // Rounding whole days absorbs the 23- and 25-hour days either side of a DST
  // change, which a plain floor would get wrong once a year.
  const days = Math.round((midnight(end) - midnight(new Date(now))) / 86_400_000);

  const date = end.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  if (days <= 0) return `Closes today, ${date}`;
  if (days === 1) return `Closes tomorrow, ${date}`;
  return `Closes in ${days} days, ${date}`;
}
