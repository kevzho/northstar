/**
 * Waypoints, the course-plot grammar for progress.
 *
 * Steps render as nodes on a course line: done is a filled star-white
 * node, upcoming is a hollow one, and the current step is Polaris, the
 * single warm light in an otherwise monochrome sky (--polaris, the one
 * color in the system that is not data). Connectors show travel: solid
 * behind you, dashed ahead.
 *
 * Purely presentational; each caller derives states from its own data.
 */

export type WaypointState = "done" | "current" | "upcoming";

export function WaypointPath({
  steps,
  ariaLabel,
  className = "",
}: {
  steps: { label?: string; state: WaypointState }[];
  ariaLabel: string;
  className?: string;
}) {
  return (
    <ol aria-label={ariaLabel} className={`flex w-full items-start ${className}`}>
      {steps.map((step, index) => (
        <li
          key={index}
          className={`flex items-start ${index > 0 ? "min-w-0 flex-1" : ""}`}
        >
          {index > 0 ? (
            <div
              aria-hidden
              className={`mt-2 min-w-3 flex-1 ${
                steps[index - 1].state === "done"
                  ? "h-px bg-star/60"
                  : "h-0 border-t border-dashed border-border"
              }`}
            />
          ) : null}
          <div className="flex flex-col items-center gap-1.5">
            <span className="flex h-4 w-4 items-center justify-center">
              {step.state === "done" ? (
                <span className="h-2.5 w-2.5 rounded-full bg-star" />
              ) : step.state === "current" ? (
                <span
                  className="flex h-4 w-4 items-center justify-center rounded-full border"
                  style={{
                    borderColor: "var(--polaris)",
                    boxShadow: "0 0 10px 1px var(--polaris-glow)",
                  }}
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: "var(--polaris)" }}
                  />
                </span>
              ) : (
                <span className="h-2.5 w-2.5 rounded-full border border-aurora-dim" />
              )}
            </span>
            {step.label ? (
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {step.label}
              </span>
            ) : null}
            <span className="sr-only">
              {step.state === "done"
                ? "completed"
                : step.state === "current"
                  ? "current step"
                  : "upcoming"}
            </span>
          </div>
        </li>
      ))}
    </ol>
  );
}
