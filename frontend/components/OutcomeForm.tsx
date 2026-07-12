"use client";

/**
 * Quick outcome-logging form rendered below the apply button on the
 * opportunity detail page. The MVP shows a dropdown of statuses + an
 * optional impact notes field. Successful submit shows a confirmation
 * banner.
 */

import { useState } from "react";
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
      <div className="mt-6 rounded-md border border-[var(--northstar)] bg-[var(--panel)] p-4">
        <p className="text-sm font-semibold text-[var(--northstar-dark)]">
          Outcome logged.
        </p>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Your result helps the pathway engine tune future recommendations.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-6 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-4">
      <h3 className="text-sm font-semibold text-[var(--foreground)]">
        Log your outcome
      </h3>
      <p className="mt-1 text-xs text-[var(--muted)]">
        Let Northstar know what happened — it improves future matches.
      </p>

      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="h-10 rounded-md border border-[var(--border)] bg-white px-3 text-sm font-semibold text-[var(--foreground)] outline-none focus:border-[var(--northstar)]"
        >
          <option value="">Select status</option>
          {statuses.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Impact notes (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="h-10 flex-1 rounded-md border border-[var(--border)] bg-white px-3 text-sm text-[var(--foreground)] outline-none placeholder:text-[var(--muted)] focus:border-[var(--northstar)]"
        />

        <button
          type="button"
          onClick={handleLog}
          disabled={submitting || !status}
          className="h-10 rounded-md bg-[var(--northstar)] px-4 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Saving..." : "Log"}
        </button>
      </div>

      {error ? (
        <p className="mt-2 text-xs font-medium text-[var(--amber)]">
          Could not save outcome. Try again?
        </p>
      ) : null}
    </div>
  );
}