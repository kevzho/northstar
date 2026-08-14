"use client";

import { useRef } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { MotionConfig, motion, useScroll, useTransform } from "motion/react";
import { useTheme } from "next-themes";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { HorizonWaves } from "@/components/decor/horizon-waves";
import { AnimatedGroup } from "@/components/motion/animated-group";
import { InView } from "@/components/motion/in-view";
import { TextEffect } from "@/components/motion/text-effect";

/* three.js stays out of the initial bundle; the sky fades in after mount. */
const Starfield = dynamic(() => import("@/components/decor/starfield"), {
  ssr: false,
});

const waypoints = [
  {
    mark: "01",
    planet: "moon" as const,
    title: "Trait profile",
    description:
      "Eight behavioral prompts become six interpretable signals: builder, analyst, risk, ambiguity, collaboration, and tempo. No black box — every score is a sum you can check.",
  },
  {
    mark: "02",
    planet: "ringed" as const,
    title: "Future paths",
    description:
      "Your traits are compared against archetypes to surface three directions: the steady fit, the stretch, and the one nobody had time to suggest.",
  },
  {
    mark: "03",
    planet: "giant" as const,
    title: "Real opportunities",
    description:
      "A TF-IDF match engine ranks curated STEM programs against your interests and goals, explains every score, and maps the pathways between them.",
  },
];

/*
 * Minimal planet renderings for the waypoint pathway: a small moon, a ringed
 * world, and a giant — all monochrome gradients, no imagery.
 */
function Planet({ kind }: { kind: "moon" | "ringed" | "giant" }) {
  const size =
    kind === "moon" ? "h-8 w-8" : kind === "ringed" ? "h-10 w-10" : "h-14 w-14";
  return (
    <div className="relative flex h-14 w-14 shrink-0 items-center justify-center">
      <div
        className={`${size} rounded-full bg-[radial-gradient(circle_at_32%_28%,var(--star-bright),var(--aurora-dim))]`}
      />
      {kind === "ringed" ? (
        <div
          aria-hidden
          className="absolute h-14 w-14 rounded-full border border-aurora-dim/70 [transform:rotateX(68deg)_rotateZ(-16deg)]"
        />
      ) : null}
    </div>
  );
}

/* Line-art rocket, nose down — it rides the waypoint pathway with scroll. */
function Ship({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 32"
      aria-hidden="true"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinejoin="round"
      strokeLinecap="round"
    >
      <path d="M12 30c3-2.6 4.8-6.2 4.8-10.2V12L12 3 7.2 12v7.8C7.2 23.8 9 27.4 12 30Z" />
      <circle cx="12" cy="14" r="2.2" />
      <path d="M7.2 17.5 3.5 21.5M16.8 17.5l3.7 4" />
    </svg>
  );
}

/* The Northstar mark — a four-point star with a counter-star cut out. */
function StarGlyph({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      aria-hidden="true"
      className={className}
      fill="currentColor"
    >
      <path
        fillRule="evenodd"
        d="M50 0Q56 40 100 50 56 60 50 100 44 60 0 50 44 40 50 0ZM50 28Q54 46 72 50 54 54 50 72 46 54 28 50 46 46 50 28Z"
      />
    </svg>
  );
}

/*
 * Ursa Minor, hand-plotted. The line draws itself on load (pathLength
 * normalizes the two subpaths to the CSS dash length) and ends at Polaris,
 * which stays lit. Decorative only — hidden from assistive tech.
 */
function Constellation() {
  const scatter = [
    [30, 60, 1.4],
    [352, 300, 1.2],
    [60, 150, 1.1],
    [330, 200, 1.6],
    [210, 330, 1.2],
    [120, 90, 1.0],
    [260, 250, 1.3],
    [40, 260, 1.5],
    [370, 90, 1.1],
    [180, 40, 1.2],
    [310, 350, 1.0],
    [90, 380, 1.3],
    [240, 110, 1.0],
    [345, 30, 1.4],
    [25, 340, 1.1],
  ] as const;
  const stars = [
    [80, 330, 3],
    [150, 340, 2.6],
    [170, 280, 2.4],
    [100, 270, 2.6],
    [150, 210, 2.4],
    [210, 150, 2.8],
  ] as const;

  return (
    <svg
      viewBox="0 0 400 400"
      aria-hidden="true"
      className="mx-auto block w-full max-w-md"
    >
      {/* faint declination arcs — chart paper, not decoration for its own sake */}
      <circle
        cx="290"
        cy="80"
        r="150"
        fill="none"
        stroke="var(--border)"
        strokeWidth="0.5"
        opacity="0.5"
      />
      <circle
        cx="290"
        cy="80"
        r="240"
        fill="none"
        stroke="var(--border)"
        strokeWidth="0.5"
        opacity="0.35"
      />

      {scatter.map(([x, y, r], i) => (
        <circle
          key={`s${i}`}
          cx={x}
          cy={y}
          r={r}
          fill="var(--foreground)"
          opacity="0.35"
          className="constellation-star"
          style={{ animationDelay: `${0.1 + i * 0.12}s` }}
        />
      ))}

      <path
        d="M80 330 L150 340 L170 280 L100 270 L80 330 M100 270 L150 210 L210 150 L290 80"
        pathLength={480}
        fill="none"
        stroke="var(--aurora-dim)"
        strokeWidth="1"
        className="constellation-line"
      />

      {stars.map(([x, y, r], i) => (
        <circle
          key={`c${i}`}
          cx={x}
          cy={y}
          r={r}
          fill="var(--foreground)"
          className="constellation-star"
          style={{ animationDelay: `${0.4 + i * 0.3}s` }}
        />
      ))}

      {/* Polaris — the fixed point. Halo and star reveal together. */}
      <g className="constellation-star" style={{ animationDelay: "2.2s" }}>
        <circle
          cx="290"
          cy="80"
          r="14"
          fill="var(--star)"
          opacity="0.18"
          className="polaris-halo"
        />
        <path
          d="M290 66 293 77 304 80 293 83 290 94 287 83 276 80 287 77Z"
          fill="var(--star)"
        />
      </g>

      <text
        x="290"
        y="116"
        textAnchor="middle"
        fill="var(--muted)"
        fontSize="9"
        letterSpacing="2"
        fontFamily="var(--font-coords), monospace"
        className="constellation-star"
        style={{ animationDelay: "2.5s" }}
      >
        POLARIS
      </text>
    </svg>
  );
}

export default function Home() {
  const { resolvedTheme } = useTheme();
  const ink = resolvedTheme === "light";
  const { scrollY } = useScroll();
  const pathwayRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress: pathwayProgress } = useScroll({
    target: pathwayRef,
    offset: ["start 0.75", "end 0.75"],
  });
  const shipTop = useTransform(pathwayProgress, [0, 1], ["0%", "94%"]);
  const constellationY = useTransform(scrollY, [0, 600], [0, -70]);
  const constellationOpacity = useTransform(scrollY, [0, 600], [1, 0.3]);

  return (
    <MotionConfig reducedMotion="user">
    <main className="min-h-screen">
      <Starfield ink={ink} className="pointer-events-none fixed inset-0 -z-10" />
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-8 sm:px-8 lg:px-10">
        <nav className="sticky top-0 z-40 -mx-2 flex items-center justify-between border-b border-border bg-background/80 px-2 py-4 backdrop-blur">
          <Link
            href="/"
            className="flex items-center gap-2 text-lg tracking-tight text-foreground"
          >
            <StarGlyph className="h-4 w-4 text-star" />
            <span className="h-display text-xl">Northstar</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-semibold text-aurora"
            >
              Sign in
            </Link>
            <Button render={<Link href="/assessment" />} className="px-4 py-2 font-semibold">
              Start assessment
            </Button>
            <ThemeToggle />
          </div>
        </nav>

        <div className="grid flex-1 items-center gap-12 py-14 lg:grid-cols-[1.1fr_0.9fr]">
          <AnimatedGroup
            preset="blur-slide"
            className="grid gap-0"
          >
            <TextEffect
              per="char"
              preset="fade"
              as="p"
              className="eyebrow"
              speedReveal={2}
            >
              A student-built opportunity map
            </TextEffect>
            <h1 className="h-display mt-5 max-w-3xl text-5xl leading-[1.05] text-foreground sm:text-6xl lg:text-7xl">
              Every student deserves a{" "}
              <span className="text-star">north star</span>.
            </h1>
            <p className="mt-7 max-w-2xl text-base leading-8 text-muted-foreground sm:text-lg">
              Most students never hear about the research programs,
              scholarships, and competitions they were qualified for. Northstar
              starts with how you actually think and work — eight behavioral
              questions — and charts a course to real, ranked STEM
              opportunities with a reason attached to every one.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Button render={<Link href="/login" />} className="h-12 px-6 font-semibold">
                Sign in to start
              </Button>
              <Button variant="outline" render={<Link href="/assessment" />} className="h-12 px-6 font-semibold">
                Try the assessment first
              </Button>
            </div>
          </AnimatedGroup>

          <motion.div style={{ y: constellationY, opacity: constellationOpacity }}>
            <Constellation />
          </motion.div>
        </div>

        <section aria-label="How Northstar works" className="pb-16">
          <h2 className="h-display text-2xl text-foreground sm:text-3xl">
            How you find it
          </h2>
          {/* The pathway: three worlds along a dashed course, revealed on
              scroll — the same shape as the product itself. */}
          <div ref={pathwayRef} className="relative mt-12">
            <div
              aria-hidden
              className="absolute bottom-4 left-7 top-4 border-l border-dashed border-border"
            />
            <motion.div
              aria-hidden
              style={{ top: shipTop }}
              className="absolute left-7 z-10 -translate-x-1/2"
            >
              <Ship className="h-7 w-5 text-star" />
            </motion.div>
            {waypoints.map((waypoint, index) => (
              <InView
                key={waypoint.mark}
                once
                variants={{
                  hidden: { opacity: 0, scale: 0.6, y: 24 },
                  visible: { opacity: 1, scale: 1, y: 0 },
                }}
                transition={{ duration: 0.55, delay: index * 0.1 }}
                viewOptions={{ margin: "0px 0px -80px 0px" }}
              >
                <div className="relative flex gap-6 pb-20 last:pb-0 sm:gap-10">
                  <Planet kind={waypoint.planet} />
                  <div className="max-w-xl pt-1">
                    <p className="flex items-center gap-2 font-mono text-xs tracking-[0.2em] text-star">
                      <StarGlyph className="h-3 w-3" />
                      {waypoint.mark}
                    </p>
                    <h3 className="mt-2 text-xl font-semibold text-foreground">
                      {waypoint.title}
                    </h3>
                    <p className="mt-2 text-sm leading-7 text-muted-foreground">
                      {waypoint.description}
                    </p>
                  </div>
                </div>
              </InView>
            ))}
          </div>
        </section>

      </section>

      <HorizonWaves className="block h-28 w-full text-foreground" />
      <footer className="border-t border-border">
        <div className="mx-auto max-w-6xl px-6 py-6 sm:px-8 lg:px-10">
          <p className="font-mono text-xs tracking-wide text-muted-foreground">
            Built by a high school student for the Congressional App Challenge.
          </p>
        </div>
      </footer>
    </main>
    </MotionConfig>
  );
}
