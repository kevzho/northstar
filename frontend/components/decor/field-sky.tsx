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
 * SIZE USES A PERCEPTUAL EXPONENT, AND HERE IS THE TRADE. Three options, run
 * against a real profile of 17/17/10/9/9/9/9/8/6/6:
 *
 *   radius ∝ share          2.83:1 biggest to smallest — but area then scales
 *                           with the SQUARE, so 2.8x the share draws 8x the
 *                           ink. That is not a bigger difference, it is a
 *                           wrong one.
 *   radius ∝ √share         1.68:1 — area exactly proportional, and honest,
 *                           but a flat profile reads as ten identical dots.
 *   radius ∝ share^0.7      2.07:1 — the proportional-symbol convention, which
 *                           exists because the eye under-reads area and a
 *                           strictly area-true map looks flatter than the data.
 *
 * 0.7 it is. The exaggeration is bounded and named rather than accidental, and
 * the list below carries the exact numbers for anyone who wants them.
 *
 * The old version was worse than any of these: a +24px floor on top of √ gave
 * 1.38:1, so the base constant was doing more of the work than the data.
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
        const relative = share / top;
        // See the note above: 0.7 rather than 0.5, and no base constant.
        const size = Math.round(Math.pow(relative, 0.7) * 88);
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
                // Two more channels so the ranking survives for someone who
                // cannot judge area well: the leading fields are brighter and
                // drawn with a heavier line.
                opacity: 0.4 + relative * 0.6,
                strokeWidth: 1.1 + relative * 1.1,
              }}
            />
          </div>
        );
      })}
    </div>
  );
}
