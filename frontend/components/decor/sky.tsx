"use client";

/**
 * Sky — the quiet star layer behind every in-app page.
 *
 * The landing page runs the full three.js starfield; interior pages get
 * this instead: a fixed inline SVG of seeded star specks in the brand
 * monochrome (ink specks in the light "printed atlas" theme). Pure CSS,
 * no per-frame work — the only motion is a slow opacity twinkle on a
 * handful of brighter stars and one comet pass every 90 seconds, and
 * `prefers-reduced-motion` stills both via the global media query in
 * globals.css.
 *
 * Deterministic by design: the same 56 stars render on every visit, so
 * the sky reads as a place, not a screensaver.
 */

import { usePathname } from "next/navigation";

/** Mulberry32 — tiny seeded PRNG so the sky is identical every render. */
function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rand = mulberry32(20260817);
const STARS = Array.from({ length: 56 }, (_, i) => ({
  cx: Math.round(rand() * 1000) / 10,
  cy: Math.round(rand() * 1000) / 10,
  r: rand() < 0.82 ? 0.6 : 1.1,
  // Every seventh star breathes; the rest hold still.
  twinkle: i % 7 === 0,
  delay: Math.round(rand() * 60) / 10,
}));

export function Sky() {
  const pathname = usePathname();
  // The landing page brings its own sky (the three.js starfield).
  if (pathname === "/") return null;

  return (
    <svg
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 h-full w-full text-foreground opacity-25"
      preserveAspectRatio="xMidYMid slice"
      viewBox="0 0 100 100"
    >
      {STARS.map((star, i) => (
        <circle
          key={i}
          cx={star.cx}
          cy={star.cy}
          r={star.r / 4}
          fill="currentColor"
          className={star.twinkle ? "sky-twinkle" : undefined}
          style={
            star.twinkle ? { animationDelay: `${star.delay}s` } : undefined
          }
        />
      ))}
      {/* One comet, one quiet pass every 90 seconds, starting up-left. */}
      <g className="sky-comet" opacity="0">
        <line
          x1="8"
          y1="4"
          x2="12.4"
          y2="7"
          stroke="currentColor"
          strokeWidth="0.22"
          strokeLinecap="round"
        />
        <circle cx="12.4" cy="7" r="0.45" fill="currentColor" />
      </g>
    </svg>
  );
}
