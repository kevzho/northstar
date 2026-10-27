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
  onToggle: (stepKey: string, index: number, done: boolean) => void;
  /** Omitted below the top level: a fork of a fork is a different plan. */
  onDiverge?: (step: {
    step_key: string;
    title: string;
    category: string;
  }) => void;
  diverging?: string | null;
  forks?: Record<string, BranchStep[]>;
  depth: number;
};

/**
 * Alternatives to a step, as opposed to the moves inside it.
 *
 * Deliberately styled as asides rather than as a list of things to do: these
 * are not in the plan, they are directions the plan could have taken. Picking
 * one is a conversation with a teacher, not a button, which is why there is
 * nothing to click here.
 */
function Forks({ items }: { items?: BranchStep[] }) {
  if (!items?.length) return null;
  return (
    <ul className="mt-3 grid gap-2 border-l border-dashed border-border pl-3">
      {items.map((fork) => (
        <li key={fork.title}>
          <p className="text-sm leading-6 text-foreground">
            <span className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-muted-foreground">
              or
            </span>{" "}
            {fork.title}
          </p>
          <p className="text-xs leading-5 text-muted-foreground">{fork.detail}</p>
        </li>
      ))}
    </ul>
  );
}

export function SubSteps({
  stepKey,
  title,
  category,
  branches,
  branching,
  branchError,
  onBreakDown,
  onToggle,
  onDiverge,
  diverging,
  forks = {},
  depth,
}: Props) {
  const mine = branches[stepKey];
  const busy = branching === stepKey;
  const error = branchError[stepKey];

  /* A button at the top level, a quiet inline link below it. The control was
     the same underlined link at every depth, which made the main action on
     the page the smallest thing on the step card -- findable only by someone
     who already knew it was there. */
  const BUTTON =
    "border border-border bg-panel-raised px-3 py-1.5 text-xs font-medium " +
    "text-foreground transition hover:border-foreground disabled:opacity-60";
  const LINK =
    "text-xs font-medium text-aurora underline decoration-border " +
    "underline-offset-4 hover:text-foreground disabled:opacity-60";

  if (!mine?.length) {
    return (
      <>
        <button
          type="button"
          onClick={() => onBreakDown({ step_key: stepKey, title, category })}
          disabled={busy}
          className={depth === 0 ? `mt-3 ${BUTTON}` : `mt-2 ${LINK}`}
        >
          {busy
            ? "Breaking it down…"
            : depth === 0
              ? "Break this into steps"
              : "Break this down further"}
        </button>
        {depth === 0 && onDiverge ? (
          <button
            type="button"
            onClick={() => onDiverge({ step_key: stepKey, title, category })}
            disabled={diverging === stepKey}
            className={`mt-3 ml-2 ${BUTTON}`}
          >
            {diverging === stepKey ? "Looking…" : "Or do something else"}
          </button>
        ) : null}
        <Forks items={forks[stepKey]} />
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
      {/* Both controls sit above the list, the way the breakdown reads: the
          action you took, then the way to take it again. "Break this into
          steps" stays on screen as the state marker -- it is done, and the
          live control beside it is the one that changes anything. */}
      {depth === 0 ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className={`${BUTTON} cursor-default opacity-60`}>
            Break this into steps
          </span>
          <button
            type="button"
            onClick={() => onBreakDown({ step_key: stepKey, title, category })}
            disabled={busy}
            className={BUTTON}
          >
            {busy ? "Rewriting…" : "Break it down differently"}
          </button>
          {onDiverge ? (
            <button
              type="button"
              onClick={() => onDiverge({ step_key: stepKey, title, category })}
              disabled={diverging === stepKey}
              className={BUTTON}
            >
              {diverging === stepKey ? "Looking…" : "Or do something else"}
            </button>
          ) : null}
        </div>
      ) : null}
      <Forks items={forks[stepKey]} />
      <ol className="mt-3 grid gap-2 border-l border-aurora-dim/40 pl-3">
        {mine.map((sub, i) => {
          const childKey = `${stepKey}::branch:${i}`;
          return (
            <li key={childKey}>
              {/* The box is the whole label, so the tap target is the text and
                  not an 8px square. Ticking is a plain checkbox rather than a
                  styled div because a student using a keyboard or a screen
                  reader gets space-to-toggle and a announced state for free. */}
              <label className="flex cursor-pointer items-start gap-2">
                <input
                  type="checkbox"
                  checked={Boolean(sub.done)}
                  onChange={(event) =>
                    onToggle(stepKey, i, event.target.checked)
                  }
                  className="mt-1.5 h-3.5 w-3.5 shrink-0 cursor-pointer accent-aurora"
                />
                <span
                  className={
                    sub.done
                      ? "text-sm leading-6 text-muted-foreground line-through decoration-aurora-dim"
                      : "text-sm leading-6 text-foreground"
                  }
                >
                  {sub.title}
                </span>
              </label>
              <p className="ml-[1.375rem] text-xs leading-5 text-muted-foreground">
                {sub.detail}
              </p>
              {/* The whole feature: this sub-step is itself a step. Stop
                  offering it once the cap is reached rather than letting a
                  student press a button that the server will refuse. */}
              {depth + 1 < BRANCH_MAX_DEPTH ? (
                <div className="ml-[1.375rem]">
                <SubSteps
                  stepKey={childKey}
                  title={sub.title}
                  category={category}
                  branches={branches}
                  branching={branching}
                  branchError={branchError}
                  onBreakDown={onBreakDown}
                  onToggle={onToggle}
                  depth={depth + 1}
                />
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
      {/* Nested levels keep their regenerate control below their own list;
          only the top level has room for a button row. */}
      {depth > 0 ? (
        <button
          type="button"
          onClick={() => onBreakDown({ step_key: stepKey, title, category })}
          disabled={busy}
          className={`mt-2 ${LINK} text-muted-foreground`}
        >
          {busy ? "Rewriting…" : "Break it down differently"}
        </button>
      ) : null}
      {error ? (
        <p aria-live="polite" className="mt-2 text-xs leading-5 text-foreground">
          {error}
        </p>
      ) : null}
    </>
  );
}
