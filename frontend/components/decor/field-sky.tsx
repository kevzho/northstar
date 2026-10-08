"use client";

/**
 * Field interest as a sky, not a bar chart.
 *
 * Ten fields as ten worlds, each sized by its share and coloured by the same
 * value it carries everywhere else in the product. A ranked list of ten bars
 * answers "which is biggest" and nothing else; the thing a student actually
 * wants to see is the SHAPE of their interests — whether they are concentrated
 * in one place or spread across the sky — and a list makes that work to read.
 *
 * AREA IS THE SHARE, NOT WIDTH. Radius scales with the square root of the
 * percentage, because a circle drawn at 21% radius against one at 4% is five
 * times wider and twenty-five times bigger, which overstates the gap by the
 * square. Area is what the eye actually compares, so area is what is made
 * proportional.
 *
 * DETERMINISTIC PLACEMENT. A phyllotaxis spiral — the arrangement a sunflower
 * uses — ordered by share, so the largest sits at the centre and the rest fall
 * outward with even spacing and no overlap, identically on every visit. Random
 * scatter would collide the big ones and read differently each time.
 *
 * THE NUMBERS ARE NOT IN THE PICTURE, AND NEITHER ARE THE NAMES. A sky is not
 * readable by a screen reader and small shares are not readable by anyone, so
 * the real list sits beneath it carrying every field, its percentage and the
 * same coloured glyph. The visual is the summary; the list is the data.
 *
 * Labelling the worlds in place was tried twice — ten labels, then four, then
 * two — and every version crossed a neighbouring world, because the label is
 * wider than the thing it names and the spiral packs them close. A label here
 * would duplicate the row three inches below it, so it buys collisions and
 * nothing else.
 */

import { FieldPlanet } from "@/components/decor/field-planets";
import { fieldColor } from "@/lib/field-colors";
import type { OpportunityField } from "@/lib/types";

const GOLDEN_ANGLE = 137.507764;

export function FieldSky({
  scores,
  labels,
}: {
  scores: Record<string, number>;
  labels: Record<string, string>;
}) {
  const ranked = Object.entries(scores)
    .filter(([, share]) => share > 0)
    .sort((a, b) => b[1] - a[1]);

  if (ranked.length === 0) return null;
  const top = ranked[0][1] || 1;

  return (
    <div
      aria-hidden="true"
      className="relative mt-5 h-64 w-full overflow-hidden rounded-lg border border-border bg-panel-raised sm:h-72"
    >
      {ranked.map(([field, share], index) => {
        // Sunflower spiral: even spacing, no collisions, same every visit.
        const angle = (index * GOLDEN_ANGLE * Math.PI) / 180;
        // The +0.7 keeps the first world off dead centre. Starting the spiral
        // at zero put the two largest on top of each other and their labels
        // across their neighbours.
        const spread = Math.sqrt((index + 0.7) / ranked.length);
        const left = 50 + Math.cos(angle) * spread * 40;
        const topPct = 50 + Math.sin(angle) * spread * 33;
        // Area proportional to share; the biggest world fills the budget.
        const size = 24 + Math.sqrt(share / top) * 52;
        return (
          <div
            key={field}
            className="absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${left}%`, top: `${topPct}%` }}
          >
            <FieldPlanet
              field={field as OpportunityField}
              className="transition-all duration-500"
              style={{
                width: `${size}px`,
                height: `${size}px`,
                color: fieldColor(field),
                opacity: 0.55 + (share / top) * 0.45,
              }}
            />
          </div>
        );
      })}
    </div>
  );
}
