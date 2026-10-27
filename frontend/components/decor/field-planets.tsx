/**
 * Field planets, "every field is a world."
 *
 * Ten tiny line-art worlds, one per opportunity field, drawn in
 * currentColor so they print in either theme. Each form is a mnemonic,
 * not a logo: CS is a world with satellites, physics a ringed giant,
 * health carries a pulse across its equator. They ride wherever a field
 * name appears, cards, chips, the profile field map, so the same world
 * means the same thing everywhere.
 *
 * Same family as the voyage glyphs (decor/voyage.tsx), one size down:
 * these are data glyphs, sized for text lines (1em-ish, ~14-18px).
 */
import type { OpportunityField } from "@/lib/types";

const PLANET_PATHS: Record<OpportunityField, React.ReactNode> = {
  // A world with two satellites on a tilted orbit.
  cs: (
    <>
      <circle cx="12" cy="12" r="5" />
      <path d="M2.5 15.5c3.5 2.6 12 1.6 18-2.8" />
      <circle cx="4.6" cy="14.2" r="1" fill="currentColor" stroke="none" />
      <circle cx="19.2" cy="10.6" r="1" fill="currentColor" stroke="none" />
    </>
  ),
  // A cell world: membrane and nucleus.
  biology: (
    <>
      <circle cx="12" cy="12" r="7.5" />
      <circle cx="10" cy="10.5" r="2.8" />
      <circle cx="15.5" cy="15" r="1" fill="currentColor" stroke="none" />
    </>
  ),
  // A gridded globe: meridian and equator.
  math: (
    <>
      <circle cx="12" cy="12" r="7.5" />
      <ellipse cx="12" cy="12" rx="7.5" ry="3" />
      <ellipse cx="12" cy="12" rx="3" ry="7.5" />
    </>
  ),
  // The ringed giant.
  physics: (
    <>
      <circle cx="12" cy="12" r="5" />
      <ellipse
        cx="12"
        cy="12"
        rx="10"
        ry="3.2"
        transform="rotate(-18 12 12)"
      />
    </>
  ),
  // A banded world under construction: latitude plates.
  engineering: (
    <>
      <circle cx="12" cy="12" r="7.5" />
      <path d="M5.1 9.5h13.8M4.5 13h15M6.1 16.5h11.8" />
    </>
  ),
  // A binary pair sharing an orbit.
  interdisciplinary: (
    <>
      <circle cx="9" cy="13.5" r="4.5" />
      <circle cx="16.5" cy="8.5" r="3" />
    </>
  ),
  // A crescent: the terminator line where light meets shadow.
  design: (
    <>
      <circle cx="12" cy="12" r="7.5" />
      <path d="M12 4.5a7.5 7.5 0 0 1 0 15 9.5 9.5 0 0 0 0-15Z" fill="currentColor" stroke="none" />
    </>
  ),
  // A comet on the way up.
  business: (
    <>
      <circle cx="15.5" cy="8.5" r="3.5" />
      <path d="M12.5 11.5 4 20M10 9.5l-6 6M14 13.5l-6 6" />
    </>
  ),
  // A cratered moon, the archive of every impact.
  humanities: (
    <>
      <circle cx="12" cy="12" r="7.5" />
      <circle cx="9.5" cy="9.5" r="1.6" />
      <circle cx="14.5" cy="14" r="1.1" />
      <circle cx="14" cy="8.5" r="0.7" />
    </>
  ),
  // A world with a pulse across its equator.
  health: (
    <>
      <circle cx="12" cy="12" r="7.5" />
      <path d="M4.5 12h3l1.5-3 2.5 6 1.5-3h6.5" />
    </>
  ),
};

export function FieldPlanet({
  field,
  className = "h-4 w-4",
  style,
}: {
  field: OpportunityField;
  className?: string;
  /**
   * For callers that size and colour a world rather than inheriting the text
   * line, the profile's field sky draws each one at a size proportional to
   * its share, which a utility class cannot express.
   */
  style?: React.CSSProperties;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      style={style}
      className={`shrink-0 ${className}`}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
    >
      {PLANET_PATHS[field] ?? PLANET_PATHS.interdisciplinary}
    </svg>
  );
}
