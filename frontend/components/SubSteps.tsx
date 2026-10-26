"use client";

/**
 * Sub-steps, and the sub-steps of those.
 *
 * WHY RECURSION IS THE POINT. A plan step is as big as the person reading it
 * is inexperienced. "Build a web app that calculates break-even" is one line
 * to someone who has shipped before and a cliff to someone who has not, and
 * one level of breakdown just moves the cliff: "code the calculation logic" is
 * the same problem a layer down. So any sub-step can be broken down again,
 * until the next thing to do is something the student can actually start.
 *
 * WHY IT STOPS AT THREE. Depth is capped by BRANCH_MAX_DEPTH. Each generation
 * is a model call a student can press, so unbounded depth is an unbounded bill
 * on one page, and a tree twelve levels deep is an outline nobody reads -- the
 * same reason roadmap_branches holds one row per (student, step) instead of a
 * children table. Three levels is far past the point where a step is startable.
 *
 * The keys are built by composition: a sub-step of `spine:project` is
 * `spine:project::branch:0`, and its own sub-step is
 * `spine:project::branch:0::branch:1`. lib/roadmap-graph.ts reads that same
 * shape to draw them, and the backend takes any step_key, so nothing about
 * nesting is special-cased server-side.
 */

import type { BranchStep } from "@/lib/api";

/** Three generations. See the note above on why this is bounded at all. */
export const BRANCH_MAX_DEPTH = 3;

type Props = {
  stepKey: string;
  title: string;
  category: string;
  branches: Record<string, BranchStep[]>;
  branching: string | null;
  branchError: Record<string, string>;
  onBreakDown: (step: {
    step_key: string;
    title: string;
    category: string;
  }) => void;
  depth: number;
};

export function SubSteps({
  stepKey,
  title,
  category,
  branches,
  branching,
  branchError,
  onBreakDown,
  depth,
}: Props) {
  const mine = branches[stepKey];
  const busy = branching === stepKey;
  const error = branchError[stepKey];

  if (!mine?.length) {
    return (
      <>
        <button
          type="button"
          onClick={() => onBreakDown({ step_key: stepKey, title, category })}
          disabled={busy}
          className="mt-3 text-xs font-medium text-aurora underline decoration-border underline-offset-4 hover:text-foreground disabled:opacity-60"
        >
          {busy
            ? "Breaking it down…"
            : depth === 0
              ? "Break this into steps"
              : "Break this down further"}
        </button>
        {error ? (
          <p
            aria-live="polite"
            className="mt-2 text-xs leading-5 text-foreground"
          >
            {error}
          </p>
        ) : null}
      </>
    );
  }

  return (
    <>
      <ol className="mt-3 grid gap-2 border-l border-aurora-dim/40 pl-3">
        {mine.map((sub, i) => {
          const childKey = `${stepKey}::branch:${i}`;
          return (
            <li key={childKey}>
              <p className="text-sm leading-6 text-foreground">
                <span className="font-mono text-xs text-aurora">{i + 1}.</span>{" "}
                {sub.title}
              </p>
              <p className="text-xs leading-5 text-muted-foreground">
                {sub.detail}
              </p>
              {/* The whole feature: this sub-step is itself a step. Stop
                  offering it once the cap is reached rather than letting a
                  student press a button that the server will refuse. */}
              {depth + 1 < BRANCH_MAX_DEPTH ? (
                <SubSteps
                  stepKey={childKey}
                  title={sub.title}
                  category={category}
                  branches={branches}
                  branching={branching}
                  branchError={branchError}
                  onBreakDown={onBreakDown}
                  depth={depth + 1}
                />
              ) : null}
            </li>
          );
        })}
      </ol>
      {/* ASKING AGAIN. Before this, the control vanished the moment a step had
          sub-steps, so a bad breakdown was permanent -- the one row per
          (student, step) is replaced on request precisely so a student can say
          "not that". */}
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => onBreakDown({ step_key: stepKey, title, category })}
          disabled={busy}
          className="text-xs text-muted-foreground underline decoration-border underline-offset-4 transition hover:text-foreground disabled:opacity-60"
        >
          {busy ? "Rewriting…" : "Break it down differently"}
        </button>
      </div>
      {error ? (
        <p aria-live="polite" className="mt-2 text-xs leading-5 text-foreground">
          {error}
        </p>
      ) : null}
    </>
  );
}
