import Link from "next/link";

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

/* Four-point star — the Northstar glyph used across the app chrome. */
function StarGlyph({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={className}
      fill="currentColor"
    >
      <path d="M12 1.5 14.2 9.8 22.5 12 14.2 14.2 12 22.5 9.8 14.2 1.5 12 9.8 9.8Z" />
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
    <main className="min-h-screen">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-8 sm:px-8 lg:px-10">
        <nav className="flex items-center justify-between border-b border-[var(--border)] pb-5">
          <Link
            href="/"
            className="flex items-center gap-2 text-lg tracking-tight text-[var(--foreground)]"
          >
            <StarGlyph className="h-4 w-4 text-[var(--star)]" />
            <span className="h-display text-xl">Northstar</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-semibold text-[var(--aurora)]"
            >
              Sign in
            </Link>
            <Link href="/assessment" className="btn-primary px-4 py-2">
              Start assessment
            </Link>
          </div>
        </nav>

        <div className="grid flex-1 items-center gap-12 py-14 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="eyebrow">A student-built opportunity map</p>
            <h1 className="h-display mt-5 max-w-3xl text-5xl leading-[1.05] text-[var(--foreground)] sm:text-6xl lg:text-7xl">
              Every student deserves a{" "}
              <span className="italic text-[var(--star)]">north star</span>.
            </h1>
            <p className="mt-7 max-w-2xl text-base leading-8 text-[var(--muted)] sm:text-lg">
              Most students never hear about the research programs,
              scholarships, and competitions they were qualified for. Northstar
              starts with how you actually think and work — eight behavioral
              questions — and charts a course to real, ranked STEM
              opportunities with a reason attached to every one.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link href="/login" className="btn-primary h-12 px-6">
                Sign in to start
              </Link>
              <Link href="/assessment" className="btn-secondary h-12 px-6">
                Try the assessment first
              </Link>
            </div>
          </div>

          <Constellation />
        </div>

        <section aria-label="How Northstar works" className="pb-16">
          <h2 className="h-display text-2xl text-[var(--foreground)] sm:text-3xl">
            How you find it
          </h2>
          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            {waypoints.map((waypoint) => (
              <article key={waypoint.mark} className="card p-5">
                <p className="flex items-center gap-2 font-mono text-xs tracking-[0.2em] text-[var(--star)]">
                  <StarGlyph className="h-3 w-3" />
                  {waypoint.mark}
                </p>
                <h3 className="mt-4 text-xl font-semibold text-[var(--foreground)]">
                  {waypoint.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                  {waypoint.description}
                </p>
              </article>
            ))}
          </div>
        </section>

        <footer className="border-t border-[var(--border)] py-6">
          <p className="font-mono text-xs tracking-wide text-[var(--muted)]">
            Built by a high school student for the Congressional App Challenge.
          </p>
        </footer>
      </section>
    </main>
  );
}
