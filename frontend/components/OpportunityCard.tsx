/**
 * Opportunity card used on the opportunities list and the dashboard. Pure
 * presentational component over the Opportunity type; data fetch lives in
 * lib/api.ts. When `onDismiss` is provided the card offers "Not for me" —
 * the cheapest negative signal the profile can collect.
 */
import Link from "next/link";
import { FieldPlanet } from "@/components/decor/field-planets";
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

/**
 * How you get in, said as a verb.
 *
 * "Apply" and "qualify" are different answers to the only question a student
 * has — can I enter this? — and the card showed neither until now. A 9th grader
 * scanning for something to do should be able to see, without opening anything,
 * that USAMO is not a thing you apply to.
 */
const gateVerbs: Record<string, string> = {
  apply: "Apply",
  qualify: "Qualify first",
  advance: "Advance from a round",
  nominate: "By nomination",
  teacher: "A teacher registers you",
};

const typeLabels: Record<OpportunityType, string> = {
  program: "Program",
  scholarship: "Scholarship",
  competition: "Competition",
  mentorship: "Mentorship",
  internship: "Internship",
  volunteer: "Volunteer",
  journal: "Journal",
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
        <span className="tabular font-mono text-xs text-muted-foreground">
          {left !== null && left < 0 ? (
            <span className="opacity-60">closed {due}</span>
          ) : left !== null && left <= 30 ? (
            <span className="text-star">
              closes in {left === 0 ? "less than a day" : `${left} day${left === 1 ? "" : "s"}`}
            </span>
          ) : opportunity.deadline ? (
            due
          ) : (
            /* No date is not a date. "Rolling" is the catalog declining to make
               a claim it has not checked, so it takes the overprint rather than
               sitting in the same ink as a deadline read off the programme's
               own page. See --advisory in app/globals.css. */
            <span className="advisory">{due}</span>
          )}
        </span>
      </div>
      <h2 className="mt-3 text-xl font-semibold leading-tight text-foreground">
        {opportunity.title}
      </h2>
      <p className="mt-1 text-sm font-medium text-muted-foreground">
        {opportunity.host}
      </p>
      {/* Two lines, not six. Most of these blurbs are the organiser's own
          marketing, scraped: FortID's ran to six lines and truncated mid-word
          on "eIDAS 2.0 compliant digit". On a shelf of 166 the job is scanning,
          and a wall of someone else's copy is what stops you. The detail page
          is one click away and carries the whole thing. */}
      <p className="mt-3 line-clamp-2 text-sm leading-6 text-muted-foreground">
        {opportunity.blurb}
      </p>
      {/* The two facts that decide whether this is worth a click, given the
          same prominence as each other: what it costs, and whether you can
          actually enter it. */}
      <p className="mt-3 flex flex-wrap items-baseline gap-x-3 gap-y-1 font-mono text-xs">
        <span className={opportunity.cost === 0 ? "text-foreground" : "text-muted-foreground"}>
          {opportunity.cost === 0 ? "Free to enter" : `$${opportunity.cost}`}
        </span>
        {opportunity.entry_gate ? (
          <span className="text-muted-foreground">
            {gateVerbs[opportunity.entry_gate] ?? "Apply"}
          </span>
        ) : null}
        {opportunity.grade_min && opportunity.grade_max ? (
          <span className="tabular text-muted-foreground">
            grades {opportunity.grade_min}–{opportunity.grade_max}
          </span>
        ) : null}
      </p>
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs font-semibold text-aurora">
            <FieldPlanet field={opportunity.field} className="h-4 w-4" />
            {fieldLabels[opportunity.field]}
          </span>
          {opportunity.location_scope ? (
            <span className="border border-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              {opportunity.location_scope === "us"
                ? "US"
                : opportunity.location_scope === "international"
                  ? "Intl"
                  : "Global"}
            </span>
          ) : null}
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
