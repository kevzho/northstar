/**
 * Opportunity card used on the opportunities list and the dashboard. Pure
 * presentational component over the Opportunity type; data fetch lives in
 * lib/api.ts.
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
};

const typeLabels: Record<OpportunityType, string> = {
  program: "Program",
  scholarship: "Scholarship",
  competition: "Competition",
  mentorship: "Mentorship",
};

export function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  const due = opportunity.deadline
    ? new Date(opportunity.deadline).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Rolling deadline";

  return (
    <article className="card card-hover p-5">
      <div className="flex items-center justify-between gap-3">
        <span className="font-mono text-xs uppercase tracking-[0.16em] text-[var(--aurora)]">
          {typeLabels[opportunity.type]}
        </span>
        <span className="font-mono text-xs text-[var(--muted)]">{due}</span>
      </div>
      <h2 className="mt-3 text-xl font-semibold text-[var(--foreground)]">
        {opportunity.title}
      </h2>
      <p className="mt-1 text-sm font-medium text-[var(--muted)]">
        {opportunity.host}
      </p>
      <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
        {opportunity.blurb}
      </p>
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-xs font-semibold text-[var(--aurora)]">
          {fieldLabels[opportunity.field]}
        </span>
        <Link
          href={`/opportunities/${opportunity.id}`}
          className="text-sm font-semibold text-[var(--star)] transition hover:text-[var(--star-bright)]"
        >
          View details
        </Link>
      </div>
    </article>
  );
}
