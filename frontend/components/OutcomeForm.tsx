"use client";

/**
 * Quick outcome-logging form rendered below the apply button on the
 * opportunity detail page. The MVP shows a dropdown of statuses + an
 * optional impact notes field. Successful submit shows a confirmation
 * banner.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { logOutcome } from "@/lib/api";

const statuses = [
  { value: "accepted", label: "Accepted" },
  { value: "rejected", label: "Rejected" },
  { value: "waitlisted", label: "Waitlisted" },
  { value: "withdrew", label: "Withdrew" },
  { value: "completed", label: "Completed" },
];

export function OutcomeForm({ opportunityId }: { opportunityId: string }) {
  const [status, setStatus] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(false);

  async function handleLog() {
    if (!status) return;
    setSubmitting(true);
    setError(false);
    try {
      await logOutcome(opportunityId, status, notes || undefined);
      setDone(true);
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <div className="mt-6 rounded-md border border-[var(--success-border)] bg-[var(--success-bg)] p-4">
        <p className="text-sm font-semibold text-[var(--success-text)]">
          Outcome logged.
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Your result re-weights the pathway graph behind future
          recommendations.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-6 rounded-lg border bg-card p-4">
      <h3 className="text-sm font-semibold text-foreground">
        Log your outcome
      </h3>
      <p className="mt-1 text-xs text-muted-foreground">
        Tell Northstar what happened — it improves future matches.
      </p>

      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <NativeSelect
          value={status}
          aria-label="Outcome status"
          onChange={(e) => setStatus(e.target.value)}
          className="h-10"
        >
          <option value="">Select status</option>
          {statuses.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </NativeSelect>

        <Input
          type="text"
          placeholder="Impact notes (optional)"
          aria-label="Impact notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="h-10 flex-1 bg-panel-raised"
        />

        <Button
          onClick={handleLog}
          disabled={submitting || !status}
          className="h-10 px-4 font-semibold"
        >
          {submitting ? "Saving..." : "Log outcome"}
        </Button>
      </div>

      {error ? (
        <p className="mt-2 text-xs font-medium text-[var(--error-text)]">
          Could not save the outcome. Try again.
        </p>
      ) : null}
    </div>
  );
}
