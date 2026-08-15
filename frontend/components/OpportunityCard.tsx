/**
 * Opportunity card used on the opportunities list and the dashboard. Pure
 * presentational component over the Opportunity type; data fetch lives in
 * lib/api.ts. When `onDismiss` is provided the card offers "Not for me" —
 * the cheapest negative signal the profile can collect.
 */
import Link from "next/link";
import type { Opportunity, OpportunityField, OpportunityType } from "@/lib/types";

const fieldLabels: Record<OpportunityField, string> = {
  cs: "Computer Science",
  biology: "Biology",
  math: "Math",
  physics: "Physics",
  engineering: "Engineering",
  interdisciplinary: "Interdisciplinary",
  design: "Design & Media",
  business: "Business",
  humanities: "Humanities",
  health: "Health",
};

const typeLabels: Record<OpportunityType, string> = {
  program: "Program",
  scholarship: "Scholarship",
  competition: "Competition",
  mentorship: "Mentorship",
};

/** Days until the deadline, or null for rolling/absent deadlines. */
function daysLeft(deadline: string | null): number | null {
  if (!deadline) return null;
  const due = new Date(`${deadline}T23:59:59`);
  if (Number.isNaN(due.getTime())) return null;
  return Math.ceil((due.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
}

export function OpportunityCard({
  opportunity,
  onDismiss,
}: {
  opportunity: Opportunity;
  onDismiss?: () => void;
}) {
  const due = opportunity.deadline
    ? new Date(opportunity.deadline).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Rolling deadline";
  const left = daysLeft(opportunity.deadline);

  return (
    <article className="rounded-lg border bg-card transition-colors hover:border-primary p-5">
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-xs uppercase tracking-[0.16em] text-aurora">
          {typeLabels[opportunity.type]}
        </span>
        <span className="font-mono text-xs text-muted-foreground">
          {left !== null && left < 0 ? (
            <span className="opacity-60">closed {due}</span>
          ) : left !== null && left <= 30 ? (
            <span className="text-star">
              closes in {left === 0 ? "less than a day" : `${left} day${left === 1 ? "" : "s"}`}
            </span>
          ) : (
            due
          )}
        </span>
      </div>
      <h2 className="mt-3 text-xl font-semibold text-foreground">
        {opportunity.title}
      </h2>
      <p className="mt-1 text-sm font-medium text-muted-foreground">
        {opportunity.host}
      </p>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        {opportunity.blurb}
      </p>
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-xs font-semibold text-aurora">
          {fieldLabels[opportunity.field]}
        </span>
        <span className="flex items-center gap-4">
          {onDismiss ? (
            <button
              type="button"
              onClick={onDismiss}
              className="text-sm font-medium text-muted-foreground transition hover:text-foreground"
            >
              Not for me
            </button>
          ) : null}
          <Link
            href={`/opportunities/${opportunity.id}`}
            className="text-sm font-semibold text-star transition hover:text-star-bright"
          >
            View details
          </Link>
        </span>
      </div>
    </article>
  );
}
