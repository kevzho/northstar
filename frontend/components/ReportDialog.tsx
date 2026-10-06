"use client";

/**
 * ReportDialog — the safety valve on every social surface.
 *
 * Reports go to a human moderation queue; the reported student never
 * sees who filed. The optional "also block" checkbox is the hard wall:
 * it removes the connection and hides both students from each other in
 * discover, team-up, and friend requests.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import { blockStudent, reportStudent, type ReportReason } from "@/lib/api";

const REASONS: { value: ReportReason; label: string }[] = [
  { value: "inappropriate", label: "Inappropriate content" },
  { value: "harassment", label: "Harassment or bullying" },
  { value: "impersonation", label: "Impersonation / fake profile" },
  { value: "spam", label: "Spam" },
  { value: "other", label: "Something else" },
];

export type ReportTarget = {
  student_id: string;
  name: string;
  handle?: string | null;
};

export function ReportDialog({
  target,
  onClose,
  onBlocked,
}: {
  target: ReportTarget;
  onClose: () => void;
  /** Called after a successful block so the parent can refresh its lists. */
  onBlocked?: () => void;
}) {
  const [reason, setReason] = useState<ReportReason>("inappropriate");
  const [details, setDetails] = useState("");
  const [alsoBlock, setAlsoBlock] = useState(false);
  const [state, setState] = useState<"idle" | "sending" | "done" | "failed">(
    "idle",
  );

  async function submit() {
    setState("sending");
    try {
      await reportStudent({
        student_id: target.student_id,
        reason,
        details: details.trim() || undefined,
      });
      if (alsoBlock) {
        await blockStudent(target.student_id);
        onBlocked?.();
      }
      setState("done");
    } catch {
      setState("failed");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={`Report ${target.name}`}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-lg border bg-card p-6"
        onClick={(event) => event.stopPropagation()}
      >
        {state === "done" ? (
          <>
            <h2 className="h-display text-section text-foreground">
              Report sent
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Thank you — a moderator will review it. They won&apos;t know it
              came from you.
              {alsoBlock ? " You won't see each other on Northstar anymore." : ""}
            </p>
            <Button onClick={onClose} className="mt-5 h-10 px-4">
              Done
            </Button>
          </>
        ) : (
          <>
            <h2 className="h-display text-section text-foreground">
              Report {target.name}
              {target.handle ? (
                <span className="ml-2 font-mono text-xs font-normal text-aurora">
                  @{target.handle}
                </span>
              ) : null}
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Reports are reviewed by a human and are never shown to the
              student you report.
            </p>

            <label className="mt-4 block text-xs font-semibold text-foreground">
              What happened?
              <NativeSelect
                value={reason}
                onChange={(event) =>
                  setReason(event.target.value as ReportReason)
                }
                className="mt-1.5 w-full"
              >
                {REASONS.map((entry) => (
                  <option key={entry.value} value={entry.value}>
                    {entry.label}
                  </option>
                ))}
              </NativeSelect>
            </label>

            <label className="mt-3 block text-xs font-semibold text-foreground">
              Anything a moderator should know? (optional)
              <Textarea
                value={details}
                onChange={(event) => setDetails(event.target.value)}
                maxLength={2000}
                className="mt-1.5"
                placeholder="What they said or did…"
              />
            </label>

            <label className="mt-3 flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                checked={alsoBlock}
                onChange={(event) => setAlsoBlock(event.target.checked)}
                className="h-4 w-4 accent-primary"
              />
              Also block {target.name} — you won&apos;t see each other again
            </label>

            {state === "failed" ? (
              <p className="mt-3 text-sm text-destructive">
                Sending failed — check your connection and try again.
              </p>
            ) : null}

            <div className="mt-5 flex gap-2">
              <Button
                onClick={submit}
                disabled={state === "sending"}
                className="h-10 px-4"
              >
                {state === "sending" ? "Sending…" : "Send report"}
              </Button>
              <Button variant="outline" onClick={onClose} className="h-10 px-4">
                Cancel
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
