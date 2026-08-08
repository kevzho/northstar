"use client";

/**
 * Opportunity detail body.
 *
 * This has to be a client component. GET /opportunities/:id is auth-gated, and
 * the access token lives in the browser (supabase-js stores the session in
 * localStorage). Fetching from the server component that owns the route meant
 * `authedFetch` always sent an anonymous request, the backend answered 401, and
 * every detail page rendered as a 404 — including the ones reached from the
 * dashboard and the pathway map.
 *
 * The route file stays a server component and just unwraps `params`.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchOpportunity } from "@/lib/api";
import type { Opportunity } from "@/lib/types";
import { BookmarkButton } from "@/components/BookmarkButton";
import { OutcomeForm } from "@/components/OutcomeForm";

export function OpportunityDetail({ id }: { id: string }) {
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const result = await fetchOpportunity(id);
      if (!cancelled) {
        setOpportunity(result);
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

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

        {loading ? (
          <section className="mt-10 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-8 text-center shadow-sm">
            <p className="text-sm font-semibold text-[var(--muted)]">
              Loading opportunity...
            </p>
          </section>
        ) : !opportunity ? (
          <section className="mt-10 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-8 text-center shadow-sm">
            <h1 className="text-2xl font-semibold tracking-tight text-[var(--northstar-dark)]">
              Opportunity not found
            </h1>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              This listing may have been removed, or your session expired. Sign
              in again and reopen it from your recommendations.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Link
                href="/opportunities"
                className="inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
              >
                Back to opportunities
              </Link>
              <Link
                href="/login"
                className="inline-flex h-11 items-center justify-center rounded-md border border-[var(--border)] bg-white px-5 text-sm font-semibold text-[var(--northstar-dark)] transition hover:border-[var(--northstar)]"
              >
                Sign in
              </Link>
            </div>
          </section>
        ) : (
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
