/**
 * Shared voyage glyphs — the minimal worlds and the rocket that travels
 * between them. Used by the landing pathway and the 30-day mission plan so
 * the "interplanetary journey" reads as one system across pages.
 */

export function Planet({ kind }: { kind: "moon" | "ringed" | "giant" }) {
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

/* Line-art rocket, nose down — it rides pathways with scroll. */
export function Ship({ className }: { className?: string }) {
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
