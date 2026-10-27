/**
 * The conforming text alternative to the orbital map.
 *
 * components/PathwayMap.tsx says it plainly: the SVG is "decorative and mouse-only.
 * Keyboard and screen reader users need the conforming list alternative." This
 * is that alternative. It is not a summary of the picture, it carries the same
 * information, from the same data, in the same order, and its links go to the
 * same place the planets do.
 *
 * WHAT THE PICTURE ENCODES, AND HOW THIS ENCODES IT
 *
 *   picture                           here
 *   ------------------------------    ---------------------------------------
 *   one star per field                one <h3> per field
 *   systems sorted by planet count    fields in that same order
 *   inner orbit = soonest deadline    an <ol>, soonest first, position = orbit
 *   outermost = rolling deadline      sorts last, labelled "rolling"
 *   click a planet                    the same /opportunities/:id link
 *
 * An ordered list is the honest shape for this. The map's whole claim is that
 * distance from the star means urgency, and "first, second, third" says that
 * without asking anyone to judge a radius by eye.
 *
 * ONE DELIBERATE DIFFERENCE. The map draws `.slice(0, 8)` planets per field,
 * because a ninth orbit does not fit in the cell. This list draws all of them.
 * An alternative is allowed to carry more than the picture, it is not allowed
 * to carry less, and silently dropping a student's ninth-most-urgent match
 * from the only view they can operate would be the exact failure this file
 * exists to fix.
 */

import Link from "next/link";
import { type PathwayNode, groupByField, whenLabel } from "@/lib/pathways";

export type { PathwayNode };

export function PathwayList({
  nodes,
  fieldColors,
}: {
  nodes: PathwayNode[];
  fieldColors: Record<string, string>;
}) {
  const systems = groupByField(nodes);

  return (
    <div className="mt-8 space-y-10">
      {systems.map(({ field, items }) => (
        <section key={field} aria-labelledby={`field-${field}`}>
          <h3
            id={`field-${field}`}
            className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-foreground"
          >
            <span
              aria-hidden="true"
              className="inline-block h-3 w-3 rounded-full"
              style={{ backgroundColor: fieldColors[field] ?? "#9e9e9e" }}
            />
            <span className="capitalize">{field}</span>
            <span className="font-normal normal-case text-muted-foreground">
              — {items.length} {items.length === 1 ? "match" : "matches"},
              most urgent first
            </span>
          </h3>

          <ol className="mt-4 space-y-px">
            {items.map((node) => (
              <li key={node.id}>
                <Link
                  href={`/opportunities/${node.id}`}
                  className="flex flex-col gap-1 border border-transparent border-b-border px-2 py-3 hover:bg-card focus-visible:border-foreground focus-visible:outline-none sm:flex-row sm:items-baseline sm:justify-between sm:gap-4"
                >
                  <span className="text-base leading-6 text-foreground">
                    {node.title}
                  </span>
                  <span className="shrink-0 font-mono text-xs text-muted-foreground">
                    {whenLabel(node.deadline)}
                    <span className="sr-only">. Opportunity type: {node.type}.</span>
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
