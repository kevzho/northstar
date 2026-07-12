/**
 * Opportunity detail page.
 *
 * Next.js 16 convention: dynamic-route `params` is a Promise and must be awaited
 * (per node_modules/next/dist/docs/.../03-layouts-and-pages.md). We use the
 * generated `PageProps<'/opportunities/[id]'>` global helper so the type stays
 * in sync with the route tree without manual maintenance.
 *
 * Data is fetched via fetchOpportunity(id) which calls GET /opportunities/:id
 * on the FastAPI backend. Returns null on 404 or network error → renders
 * the "not found" branch below.
 */

import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchOpportunity } from "@/lib/api";
import { BookmarkButton } from "@/components/BookmarkButton";
import { OutcomeForm } from "@/components/OutcomeForm";

export default async function Page(
  props: { params: Promise<{ id: string }> },
) {
  const { id } = await props.params;
  const opportunity = await fetchOpportunity(id);

  if (!opportunity) {
    notFound();
  }

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-4xl">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-5">
          <Link
            href="/opportunities"
            className="text-lg font-semibold tracking-tight text-[var(--northstar-dark)]"
          >
            Northstar
          </Link>
          <Link
            href="/opportunities"
            className="text-sm font-semibold text-[var(--northstar)]"
          >
            Back to opportunities
          </Link>
        </div>

        {!opportunity ? null : (
          <article className="mt-10">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--amber)]">
              {opportunity.host}
            </p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[var(--northstar-dark)]">
              {opportunity.title}
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-8 text-[var(--foreground)]">
              {opportunity.description}
            </p>

            <dl className="mt-8 grid gap-4 sm:grid-cols-2">
              <div className="rounded-md border border-[var(--border)] bg-[var(--panel)] p-4">
                <dt className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                  Deadline
                </dt>
                <dd className="mt-2 text-sm text-[var(--foreground)]">
                  {opportunity.deadline
                    ? new Date(opportunity.deadline).toLocaleDateString("en-US", {
                        month: "long",
                        day: "numeric",
                        year: "numeric",
                      })
                    : "Rolling deadline"}
                </dd>
              </div>
              <div className="rounded-md border border-[var(--border)] bg-[var(--panel)] p-4">
                <dt className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                  Grade range
                </dt>
                <dd className="mt-2 text-sm text-[var(--foreground)]">
                  {opportunity.grade_min}–{opportunity.grade_max}
                </dd>
              </div>
              <div className="rounded-md border border-[var(--border)] bg-[var(--panel)] p-4">
                <dt className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                  Cost
                </dt>
                <dd className="mt-2 text-sm text-[var(--foreground)]">
                  {opportunity.cost === 0
                    ? "Fully funded"
                    : `$${opportunity.cost.toLocaleString()}`}
                </dd>
              </div>
              <div className="rounded-md border border-[var(--border)] bg-[var(--panel)] p-4">
                <dt className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                  Tags
                </dt>
                <dd className="mt-2 text-sm text-[var(--foreground)]">
                  {opportunity.tags.join(" · ") || "—"}
                </dd>
              </div>
            </dl>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <BookmarkButton opportunityId={opportunity.id} />
              <a
                href={opportunity.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-12 items-center justify-center rounded-md bg-[var(--northstar)] px-6 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
              >
                Apply
              </a>
            </div>

            <OutcomeForm opportunityId={opportunity.id} />
          </article>
        )}
      </div>
    </main>
  );
}
