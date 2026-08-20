/**
 * Orbit loader — the one loading treatment for every in-app wait.
 *
 * A tiny system in transit: two faint rings, two planets on opposite
 * tracks, a softly breathing star at the center. Monochrome by the same
 * rule as everything else (currentColor; no data, no color), and
 * `prefers-reduced-motion` stills it via the global media query.
 *
 * Pages should not hand-roll "Loading..." text anymore — render
 * <LoadingSection label="..." /> inside a page body, or
 * <LoadingScreen label="..." /> when nothing else is on screen yet.
 */

export function OrbitLoader({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      aria-hidden="true"
      className={className ?? "h-12 w-12 text-foreground"}
    >
      <circle
        cx="32"
        cy="32"
        r="13"
        fill="none"
        stroke="currentColor"
        strokeWidth="0.75"
        opacity="0.25"
      />
      <circle
        cx="32"
        cy="32"
        r="23"
        fill="none"
        stroke="currentColor"
        strokeWidth="0.75"
        opacity="0.15"
      />
      <circle className="orbit-core" cx="32" cy="32" r="3" fill="currentColor" />
      <g className="orbit-planet-a">
        <circle cx="32" cy="19" r="2" fill="currentColor" opacity="0.85" />
      </g>
      <g className="orbit-planet-b">
        <circle cx="55" cy="32" r="1.4" fill="currentColor" opacity="0.6" />
      </g>
    </svg>
  );
}

/** In-page wait: sits where the content will land, no card chrome. */
export function LoadingSection({
  label,
  className,
}: {
  label: string;
  className?: string;
}) {
  return (
    <div
      role="status"
      className={
        className ?? "mt-10 flex flex-col items-center gap-4 py-10 text-center"
      }
    >
      <OrbitLoader />
      <p className="font-mono text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

/** Whole-page wait: the route has nothing else to show yet. */
export function LoadingScreen({ label }: { label: string }) {
  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <LoadingSection label={label} className="flex flex-col items-center gap-4 text-center" />
    </main>
  );
}
