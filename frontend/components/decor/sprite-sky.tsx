"use client";

/**
 * A 2D sprite collage that leans with the pointer.
 *
 * REPLACES THE THREE.JS SKY. The old landing background was a WebGL scene -
 * three depth shells of star sprites, two spiral galaxies, two shaded planets,
 * a leaning camera. It pulled three.js into the page for decoration, and the
 * decoration read as a generic space scene rather than as anything belonging to
 * this product.
 *
 * This is 2D: ten 128px planet sprites that already shipped in public/planets,
 * laid out as a collage across three depth bands and translated against the
 * pointer. No canvas, no WebGL, no per-frame JavaScript.
 *
 * PARALLAX WITHOUT A RENDER LOOP. A pointermove handler writes two CSS custom
 * properties and nothing else; each layer's transform reads them through calc()
 * and a CSS transition does the smoothing. The browser animates on the
 * compositor, so a fast mouse costs no main-thread work and cannot drop the
 * page's own interactions.
 *
 * DETERMINISTIC, NOT RANDOM. The same ten positions render on every visit, from
 * a seeded generator, the sky reads as a place rather than a screensaver, which
 * is the principle the old in-app star layer was written on before it was
 * removed for breaking mobile layout.
 *
 * CLIPPED AND INERT. Absolutely positioned inside an overflow-clipped parent
 * with pointer-events: none, because the previous star layer put SVG circles
 * past the viewport edge and gave /opportunities a horizontal scrollbar on every
 * phone.
 */

import { useEffect, useRef } from "react";

/** Mulberry32 — the same tiny seeded PRNG the old star layer used. */
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

/**
 * Three depth bands. `depth` is how far a band travels against the pointer, in
 * pixels at full deflection, far things barely move, near things lead.
 */
const BANDS = [
  { count: 5, depth: 8, size: [26, 42], opacity: 0.16, blur: 1.1 },
  { count: 3, depth: 20, size: [52, 76], opacity: 0.26, blur: 0.4 },
  { count: 2, depth: 38, size: [96, 132], opacity: 0.34, blur: 0 },
] as const;

type Sprite = {
  src: string;
  left: number;
  top: number;
  size: number;
  depth: number;
  opacity: number;
  blur: number;
  spin: number;
};

function layout(): Sprite[] {
  const rnd = mulberry32(20261008);
  const out: Sprite[] = [];
  let planet = 0;
  for (const band of BANDS) {
    for (let i = 0; i < band.count; i++) {
      const [lo, hi] = band.size;
      out.push({
        src: `/planets/planet0${planet % 10}.png`,
        // Kept inside 4–92% so nothing hugs an edge and gets half-clipped.
        left: 4 + rnd() * 88,
        top: 4 + rnd() * 84,
        size: Math.round(lo + rnd() * (hi - lo)),
        depth: band.depth,
        opacity: band.opacity,
        blur: band.blur,
        spin: Math.round(rnd() * 360),
      });
      planet += 1;
    }
  }
  return out;
}

const SPRITES = layout();

export function SpriteSky({ className = "" }: { className?: string }) {
  const host = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = host.current;
    if (!node) return;
    // Someone who asked their machine to stop animating gets a still collage.
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

    let frame = 0;
    function onMove(event: PointerEvent) {
      if (frame) return; // coalesce to one write per frame
      frame = requestAnimationFrame(() => {
        frame = 0;
        const x = event.clientX / window.innerWidth - 0.5;
        const y = event.clientY / window.innerHeight - 0.5;
        node!.style.setProperty("--px", String(x.toFixed(3)));
        node!.style.setProperty("--py", String(y.toFixed(3)));
      });
    }
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div
      ref={host}
      aria-hidden="true"
      style={{ ["--px" as string]: "0", ["--py" as string]: "0" }}
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
    >
      {SPRITES.map((s, i) => (
        /* eslint-disable-next-line @next/next/no-img-element --
           next/image is the wrong tool for ten decorative 128px local PNGs:
           every one would become a /_next/image request to re-encode an asset
           that is already small and already shipped, and the component renders
           at a fixed pixel size with width and height set, so there is no
           layout shift for the optimiser to prevent. */
        <img
          key={i}
          src={s.src}
          alt=""
          draggable={false}
          width={s.size}
          height={s.size}
          className="sprite-sky-body absolute select-none"
          style={{
            left: `${s.left}%`,
            top: `${s.top}%`,
            width: `${s.size}px`,
            height: `${s.size}px`,
            opacity: s.opacity,
            filter: s.blur ? `blur(${s.blur}px)` : undefined,
            transform:
              `translate3d(calc(var(--px) * ${s.depth}px), ` +
              `calc(var(--py) * ${s.depth}px), 0) rotate(${s.spin}deg)`,
          }}
        />
      ))}
    </div>
  );
}
