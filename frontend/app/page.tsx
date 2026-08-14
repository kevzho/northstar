"use client";

import Link from "next/link";
import { MotionConfig } from "motion/react";
import { Button } from "@/components/ui/button";
import { HorizonWaves } from "@/components/decor/horizon-waves";
import { AnimatedGroup } from "@/components/motion/animated-group";
import { InView } from "@/components/motion/in-view";
import { TextEffect } from "@/components/motion/text-effect";

const waypoints = [
  {
    mark: "01",
    title: "Trait profile",
    description:
      "Eight behavioral prompts become six interpretable signals: builder, analyst, risk, ambiguity, collaboration, and tempo. No black box — every score is a sum you can check.",
  },
  {
    mark: "02",
    title: "Future paths",
    description:
      "Your traits are compared against archetypes to surface three directions: the steady fit, the stretch, and the one nobody had time to suggest.",
  },
  {
    mark: "03",
    title: "Real opportunities",
    description:
      "A TF-IDF match engine ranks curated STEM programs against your interests and goals, explains every score, and maps the pathways between them.",
  },
];

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
  return (
    <MotionConfig reducedMotion="user">
    <main className="min-h-screen">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-8 sm:px-8 lg:px-10">
        <nav className="flex items-center justify-between border-b border-border pb-5">
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
              <span className="italic text-star">north star</span>.
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

          <Constellation />
        </div>

        <section aria-label="How Northstar works" className="pb-16">
          <h2 className="h-display text-2xl text-foreground sm:text-3xl">
            How you find it
          </h2>
          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            {waypoints.map((waypoint, index) => (
              <InView
                key={waypoint.mark}
                once
                variants={{
                  hidden: { opacity: 0, y: 24 },
                  visible: { opacity: 1, y: 0 },
                }}
                transition={{ duration: 0.5, delay: index * 0.12 }}
                viewOptions={{ margin: "0px 0px -80px 0px" }}
              >
              <article className="h-full rounded-lg border bg-card p-5">
                <p className="flex items-center gap-2 font-mono text-xs tracking-[0.2em] text-star">
                  <StarGlyph className="h-3 w-3" />
                  {waypoint.mark}
                </p>
                <h3 className="mt-4 text-xl font-semibold text-foreground">
                  {waypoint.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {waypoint.description}
                </p>
              </article>
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
