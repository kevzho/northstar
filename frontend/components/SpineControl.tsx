"use client";

/**
 * "This path isn't mine.", the control that acts on it.
 *
 * The build and publish steps on /plan used to come from one of twenty-four
 * authored spines, picked by archetype. Two students who both land on
 * "applied-ai-builder" read the same sentence about a study-note summariser
 * whether one is a 9th grader who has shipped nothing and the other a 12th
 * grader with three projects.
 *
 * WHY THE REASON BOX IS THE POINT. A regenerate button on its own is a dice
 * roll: the model can hand back the same idea reworded and the student is no
 * better off. What they type here goes into the prompt alongside the plan they
 * turned down, with an instruction to write something genuinely different and
 * to fix the problem they named. "I don't want to do anything with AI" is more
 * useful than any trait score, because it is the student saying it directly.
 *
 * It is optional, because requiring an essay to decline a suggestion is its own
 * barrier, and "none of this fits" is a complete thought.
 *
 * WHEN THIS APPEARS UNPROMPTED. Each authored spine names a skill rung joining
 * to learning_resources, and twelve of the twenty-four point at a key with no
 * resource behind it, so those students' learn step renders as nothing at all.
 * The backend reports that as `spine_hollow`, and only then does this lead with
 * the offer, a fix where the shelf is genuinely empty, rather than a nag at
 * everyone.
 */

import { useState } from "react";
import { regenerateSpine, type GeneratedSpine } from "@/lib/api";

export function SpineControl({
  source,
  hollow,
  onReplaced,
}: {
  source: "authored" | "generated";
  /** The authored path's learn rung has no resources behind it. */
  hollow: boolean;
  onReplaced: (spine: GeneratedSpine) => void;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setBusy(true);
    setError("");
    try {
      onReplaced(await regenerateSpine(reason));
      setOpen(false);
      setReason("");
    } catch (caught) {
      // The server's own words. Every refusal here is one worth reading: out of
      // budget, model unreachable, or a path that pointed at a skill with
      // nothing behind it. In all three the current path is unchanged.
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-8 border-t border-border pt-6">
      <p className="text-sm leading-6 text-muted-foreground">
        {source === "generated" ? (
          <>
            The build and publish steps above were{" "}
            <span className="advisory">written for you</span> from your
            assessment and your matches — a suggestion, not a route anyone has
            walked.
          </>
        ) : hollow ? (
          <>
            Your path came from a set of twenty-four, and{" "}
            <span className="text-foreground">
              this one has no learning resources behind it yet
            </span>
            . A path written for you would point at a skill we can actually hand
            you something to read for.
          </>
        ) : (
          <>
            The build and publish steps above come from a set of twenty-four
            paths, chosen by your assessment. If none of it is yours, say so and
            one will be written for you.
          </>
        )}
      </p>

      {!open ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="mt-4 border border-border bg-transparent px-4 py-2 text-sm font-medium text-foreground hover:bg-card"
        >
          {source === "generated" ? "Write me a different one" : "This path isn't mine"}
        </button>
      ) : (
        <div className="mt-4 max-w-2xl">
          <label
            htmlFor="spine-reason"
            className="block text-sm font-medium text-foreground"
          >
            What doesn&apos;t fit?{" "}
            <span className="font-normal text-muted-foreground">
              Optional, but it is the part that makes the next one different.
            </span>
          </label>
          <textarea
            id="spine-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            rows={3}
            maxLength={300}
            placeholder="e.g. I don't want to build anything with AI — I'd rather do lab work."
            className="mt-2 w-full border border-border bg-transparent p-3 text-sm text-foreground placeholder:text-muted-foreground focus-visible:border-foreground focus-visible:outline-none"
          />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={submit}
              disabled={busy}
              className="border border-foreground bg-foreground px-4 py-2 text-sm font-medium text-background disabled:opacity-60"
            >
              {busy ? "Writing…" : "Write me a new path"}
            </button>
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                setError("");
              }}
              className="border border-border bg-transparent px-4 py-2 text-sm font-medium text-foreground"
            >
              Keep what I have
            </button>
          </div>
          {/* Announced, because the outcome of pressing the button is the whole
              interaction and a sighted user sees the steps above change. */}
          <p aria-live="polite" className="mt-3 text-sm leading-6">
            {busy ? (
              <span className="text-muted-foreground">
                Reading your assessment and your matches…
              </span>
            ) : error ? (
              <span className="text-foreground">{error}</span>
            ) : null}
          </p>
        </div>
      )}
    </section>
  );
}
