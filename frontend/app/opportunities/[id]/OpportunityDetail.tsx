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
import { Button } from "@/components/ui/button";
import { AppNav } from "@/components/AppNav";
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
        <AppNav
          homeHref="/opportunities"
          right={
            <Link
              href="/opportunities"
              className="text-sm font-semibold text-aurora"
            >
              Back to opportunities
            </Link>
          }
        />

        {loading ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <p className="font-mono text-sm text-muted-foreground">
              Loading opportunity...
            </p>
          </section>
        ) : !opportunity ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h1 className="h-display text-3xl text-foreground">
              Opportunity not found
            </h1>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              This listing may have been removed, or your session expired. Sign
              in again and reopen it from your recommendations.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Button render={<Link href="/opportunities" />} className="h-11 px-5 font-semibold">
                Back to opportunities
              </Button>
              <Button variant="outline" render={<Link href="/login" />} className="h-11 px-5 font-semibold">
                Sign in
              </Button>
            </div>
          </section>
        ) : (
          <article className="mt-10">
            <p className="eyebrow">{opportunity.host}</p>
            <h1 className="h-display mt-3 text-4xl text-foreground">
              {opportunity.title}
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-8 text-foreground">
              {opportunity.description}
            </p>

            <dl className="mt-8 grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg border bg-card p-4">
                <dt className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  Deadline
                </dt>
                <dd className="mt-2 text-sm text-foreground">
                  {opportunity.deadline
                    ? new Date(opportunity.deadline).toLocaleDateString("en-US", {
                        month: "long",
                        day: "numeric",
                        year: "numeric",
                      })
                    : "Rolling deadline"}
                </dd>
              </div>
              <div className="rounded-lg border bg-card p-4">
                <dt className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  Grade range
                </dt>
                <dd className="mt-2 text-sm text-foreground">
                  {opportunity.grade_min}–{opportunity.grade_max}
                </dd>
              </div>
              <div className="rounded-lg border bg-card p-4">
                <dt className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  Cost
                </dt>
                <dd className="mt-2 text-sm text-foreground">
                  {opportunity.cost === 0
                    ? "Fully funded"
                    : `$${opportunity.cost.toLocaleString()}`}
                </dd>
              </div>
              <div className="rounded-lg border bg-card p-4">
                <dt className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  Tags
                </dt>
                <dd className="mt-2 text-sm text-foreground">
                  {opportunity.tags.join(" · ") || "—"}
                </dd>
              </div>
            </dl>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <BookmarkButton opportunityId={opportunity.id} />
              <Button
                render={
                  <a href={opportunity.url} target="_blank" rel="noreferrer" />
                }
                className="h-12 px-6 font-semibold"
              >
                Apply
              </Button>
            </div>

            <OutcomeForm opportunityId={opportunity.id} />
          </article>
        )}
      </div>
    </main>
  );
}
