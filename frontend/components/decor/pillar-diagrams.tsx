/**
 * Pillar diagrams, one small figure per waypoint on the landing page.
 *
 * Each figure is the SHAPE of the thing it sits beside, not an ornament: the
 * six bars are the six real trait keys from lib/scoring.ts, the three paths are
 * the three directions /futures actually surfaces, and the ranked rows carry
 * the reason chips that /opportunities actually renders. A diagram that
 * misrepresents the product is worse than no diagram, because it is the part a
 * visitor believes without reading.
 *
 * Monochrome and palette-agnostic: everything is `currentColor` or a token, so
 * these render correctly in the night palette and inside the paper band.
 * Decorative in the accessibility tree, the prose beside them carries the
 * meaning, so announcing them twice would only add noise.
 */

import { TRAIT_KEYS } from "@/lib/scoring";

/** Stable pseudo-random bar lengths: a figure, not a real student's profile. */
const BAR_FILL: Record<string, number> = {
  builder: 0.82,
  analyst: 0.54,
  riskTolerance: 0.38,
  ambiguityComfort: 0.66,
  collaboration: 0.47,
  executionTempo: 0.73,
};

const TRAIT_LABEL: Record<string, string> = {
  builder: "builder",
  analyst: "analyst",
  riskTolerance: "risk",
  ambiguityComfort: "ambiguity",
  collaboration: "collab",
  executionTempo: "tempo",
};

/** 01 — Trait profile. Six bars, because there are exactly six trait keys. */
export function TraitBars({ className = "" }: { className?: string }) {
  const row = 15;
  const height = TRAIT_KEYS.length * row + 6;
  return (
    <svg
      aria-hidden
      viewBox={`0 0 200 ${height}`}
      className={className}
      role="presentation"
    >
      {TRAIT_KEYS.map((key, i) => {
        const y = i * row + 4;
        const fill = BAR_FILL[key] ?? 0.5;
        return (
          <g key={key}>
            <text
              x="0"
              y={y + 6}
              className="fill-current opacity-40"
              style={{ fontSize: 6, letterSpacing: "0.12em" }}
            >
              {TRAIT_LABEL[key]?.toUpperCase()}
            </text>
            {/* Track, then value. The track is what makes it read as a
                measurement rather than a bar chart of nothing. */}
            <rect x="58" y={y} width="142" height="7" className="fill-current opacity-10" />
            <rect x="58" y={y} width={142 * fill} height="7" className="fill-current opacity-70" />
          </g>
        );
      })}
    </svg>
  );
}

/** 02 — Future paths. One origin, three divergences: fit, stretch, unsuggested. */
export function ThreePaths({ className = "" }: { className?: string }) {
  const paths = [
    { d: "M6 44 C 70 44, 110 16, 194 12", label: "steady fit", dash: "" },
    { d: "M6 44 C 70 44, 110 44, 194 44", label: "the stretch", dash: "" },
    { d: "M6 44 C 70 44, 110 72, 194 78", label: "unsuggested", dash: "3 4" },
  ];
  return (
    <svg aria-hidden viewBox="0 0 200 92" className={className} role="presentation">
      {paths.map((p, i) => (
        <g key={p.label}>
          <path
            d={p.d}
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            strokeDasharray={p.dash}
            className={i === 2 ? "opacity-35" : "opacity-70"}
          />
          <rect
            x="192"
            y={[9, 41, 75][i]}
            width="6"
            height="6"
            className={i === 2 ? "fill-current opacity-45" : "fill-current opacity-90"}
          />
        </g>
      ))}
      {/* The single origin — every path starts from the same profile. */}
      <rect x="2" y="40" width="7" height="7" className="fill-current" />
    </svg>
  );
}

/**
 * 03, Real opportunities. Ranked rows with a score and the reasons behind it,
 * which is the one claim the product makes loudest: nothing is a black box.
 */
export function RankedReasons({ className = "" }: { className?: string }) {
  const rows = [
    { score: ".94", chips: [54, 30] },
    { score: ".71", chips: [40, 26] },
    { score: ".58", chips: [34, 22] },
  ];
  return (
    <svg aria-hidden viewBox="0 0 200 92" className={className} role="presentation">
      {rows.map((r, i) => {
        const y = i * 30 + 4;
        return (
          <g key={r.score}>
            {/* Hairline row, flat — the interface has no rounded corners. */}
            <rect
              x="0"
              y={y}
              width="200"
              height="24"
              className="fill-none stroke-current opacity-25"
              strokeWidth="1"
            />
            <text
              x="7"
              y={y + 16}
              className="fill-current opacity-80"
              style={{ fontSize: 9, letterSpacing: "0.06em" }}
            >
              {r.score}
            </text>
            {/* Title bar standing in for the programme name. */}
            <rect x="34" y={y + 7} width="70" height="4" className="fill-current opacity-35" />
            {/* Reason chips — the "why" attached to every score. */}
            {r.chips.map((w, c) => (
              <rect
                key={c}
                x={112 + (c === 0 ? 0 : r.chips[0] + 6)}
                y={y + 6}
                width={w}
                height="7"
                className="fill-current opacity-18"
              />
            ))}
          </g>
        );
      })}
    </svg>
  );
}

/**
 * 04, Students on the same path. Two routes that converge on shared worlds.
 *
 * Deliberately NOT a pair of avatars: the product matches on path, fields and
 * working style, never on identity, and a figure showing two people would imply
 * a social graph the matcher does not build.
 */
export function SharedOrbit({ className = "" }: { className?: string }) {
  const worlds = [46, 100, 154];
  return (
    <svg aria-hidden viewBox="0 0 200 92" className={className} role="presentation">
      {/* Two travellers, separate starts, same waypoints, different arrival. */}
      <path
        d="M6 26 C 50 26, 70 46, 100 46 C 130 46, 150 22, 194 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1"
        className="opacity-70"
      />
      <path
        d="M6 70 C 50 70, 70 46, 100 46 C 130 46, 150 72, 194 74"
        fill="none"
        stroke="currentColor"
        strokeWidth="1"
        strokeDasharray="3 4"
        className="opacity-55"
      />
      {/* The shared middle world is larger: the overlap is the point. */}
      {worlds.map((cx, i) => (
        <circle
          key={cx}
          cx={cx}
          cy="46"
          r={i === 1 ? 6 : 3.5}
          className={i === 1 ? "fill-current opacity-85" : "fill-current opacity-45"}
        />
      ))}
      <rect x="2" y="23" width="6" height="6" className="fill-current opacity-70" />
      <rect x="2" y="67" width="6" height="6" className="fill-current opacity-55" />
    </svg>
  );
}

export const PILLAR_FIGURES = {
  "01": TraitBars,
  "02": ThreePaths,
  "03": RankedReasons,
  "04": SharedOrbit,
} as const;
