/**
 * Whole calendar days until a deadline.
 *
 * THIS BUG HAS HAPPENED TWICE IN THIS CODEBASE, in two files, for the same
 * reason: measuring a remaining DURATION in milliseconds and then labelling the
 * result a day count. lib/pathways.ts#whenLabel had it and was fixed; the copy
 * inside CatalogSignals was missed, so until a stress test caught it every
 * deadline on the landing page read one day further away than it was — at 22:00
 * a thing closing tonight has two hours left, ceil(0.08) is 1, and the ticker
 * said "1d" about something that shuts before the student wakes up.
 *
 * It lives here, alone, so there is one implementation to be wrong about.
 *
 * Both sides are anchored at local noon: a deadline is a date, not an instant,
 * and noon is the only hour a DST shift cannot push across midnight.
 */
export function daysUntil(iso: string, now: number = Date.now()): number {
  const due = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(due.getTime())) return Number.NaN;
  const today = new Date(now);
  today.setHours(12, 0, 0, 0);
  return Math.round((due.getTime() - today.getTime()) / 86_400_000);
}
