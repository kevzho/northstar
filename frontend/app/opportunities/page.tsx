"use client";

/**
 * Opportunity list page.
 *
 * Lists the student's matched opportunities with filters by field and type.
 * Data is fetched through lib/api.fetchMatches() which calls GET /match on
 * the FastAPI backend. The page renders score + explanation under each card
 * and falls through to an empty state when no matches exist.
 */

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { OpportunityCard } from "@/components/OpportunityCard";
import { fetchMatches } from "@/lib/api";
import type { MatchResult, OpportunityField, OpportunityType } from "@/lib/types";

const fieldFilters: { value: OpportunityField | "all"; label: string }[] = [
  { value: "all", label: "All fields" },
  { value: "cs", label: "Computer Science" },
  { value: "biology", label: "Biology" },
  { value: "math", label: "Math" },
  { value: "physics", label: "Physics" },
  { value: "engineering", label: "Engineering" },
  { value: "interdisciplinary", label: "Interdisciplinary" },
];

const typeFilters: { value: OpportunityType | "all"; label: string }[] = [
  { value: "all", label: "All types" },
  { value: "program", label: "Programs" },
  { value: "scholarship", label: "Scholarships" },
  { value: "competition", label: "Competitions" },
  { value: "mentorship", label: "Mentorship" },
];

const fieldValues = new Set(fieldFilters.map((f) => f.value));
const typeValues = new Set(typeFilters.map((f) => f.value));

/**
 * Read a filter out of the query string, falling back to "all" for anything
 * that is not a value we render — a hand-edited or stale URL must not produce
 * a select with no matching option.
 */
function readParam<T extends string>(
  params: URLSearchParams,
  key: string,
  allowed: Set<T | "all">,
): T | "all" {
  const raw = params.get(key);
  return raw && allowed.has(raw as T) ? (raw as T) : "all";
}

function OpportunitiesList() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [matches, setMatches] = useState<MatchResult[]>([]);

  // Filters live in the URL so a reload, a back button, or a shared link keeps
  // the same view. Useful in the demo: the filtered list is linkable.
  const field = readParam<OpportunityField>(
    new URLSearchParams(searchParams.toString()),
    "field",
    fieldValues,
  );
  const type = readParam<OpportunityType>(
    new URLSearchParams(searchParams.toString()),
    "type",
    typeValues,
  );

  function setFilter(key: "field" | "type", value: string) {
    const next = new URLSearchParams(searchParams.toString());
    if (value === "all") {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  useEffect(() => {
    let mounted = true;
    fetchMatches()
      .then((result) => {
        if (mounted) setMatches(result);
      })
      .catch(() => {
        // No profile, no seed data, or backend down — fall through to the
        // empty state below rather than throwing at the route boundary.
        if (mounted) setMatches([]);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const filtered = matches.filter(({ opportunity }) => {
    if (field !== "all" && opportunity.field !== field) return false;
    if (type !== "all" && opportunity.type !== type) return false;
    return true;
  });

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-5">
          <Link
            href="/dashboard"
            className="text-lg font-semibold tracking-tight text-[var(--northstar-dark)]"
          >
            Northstar
          </Link>
          <Link
            href="/dashboard"
            className="text-sm font-semibold text-[var(--northstar)]"
          >
            Back to dashboard
          </Link>
        </div>

        <header className="mt-10">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--amber)]">
            Recommendations
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[var(--northstar-dark)]">
            Opportunities for you
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[var(--muted)]">
            Ranked by the Northstar TF-IDF match engine against your profile.
            Filter by field and type to focus the list.
          </p>
        </header>

        <section className="mt-6 flex flex-wrap gap-3">
          <select
            value={field}
            aria-label="Filter by field"
            onChange={(event) => setFilter("field", event.target.value)}
            className="h-11 rounded-md border border-[var(--border)] bg-white px-4 text-sm font-semibold text-[var(--foreground)] outline-none focus:border-[var(--northstar)]"
          >
            {fieldFilters.map((filter) => (
              <option key={filter.value} value={filter.value}>
                {filter.label}
              </option>
            ))}
          </select>
          <select
            value={type}
            aria-label="Filter by type"
            onChange={(event) => setFilter("type", event.target.value)}
            className="h-11 rounded-md border border-[var(--border)] bg-white px-4 text-sm font-semibold text-[var(--foreground)] outline-none focus:border-[var(--northstar)]"
          >
            {typeFilters.map((filter) => (
              <option key={filter.value} value={filter.value}>
                {filter.label}
              </option>
            ))}
          </select>
        </section>

        {filtered.length > 0 ? (
          <section className="mt-8 grid gap-4 md:grid-cols-2">
            {filtered.map(({ opportunity, score }) => (
              <div key={opportunity.id} className="grid gap-2">
                <OpportunityCard opportunity={opportunity} />
                <p className="px-1 text-xs text-[var(--muted)]">
                  Match score {Math.round(score.score * 100)} · {score.explanation}
                </p>
              </div>
            ))}
          </section>
        ) : matches.length > 0 ? (
          // Results exist but the current filters exclude all of them. Saying
          // "finish onboarding" here would send the student down the wrong path.
          <section className="mt-10 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-8 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-[var(--foreground)]">
              Nothing matches these filters
            </h2>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              You have {matches.length} ranked{" "}
              {matches.length === 1 ? "opportunity" : "opportunities"}, but none
              in this field and type combination.
            </p>
            <button
              type="button"
              onClick={() => router.replace(pathname, { scroll: false })}
              className="mt-6 inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
            >
              Clear filters
            </button>
          </section>
        ) : (
          <section className="mt-10 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-8 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-[var(--foreground)]">
              No recommendations yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              Take the 5-minute assessment or finish onboarding so the match
              engine has a profile to rank from.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Link
                href="/onboarding"
                className="inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
              >
                Finish onboarding
              </Link>
              <Link
                href="/assessment"
                className="inline-flex h-11 items-center justify-center rounded-md border border-[var(--border)] bg-white px-5 text-sm font-semibold text-[var(--northstar-dark)] transition hover:border-[var(--northstar)]"
              >
                Take assessment
              </Link>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

/**
 * useSearchParams() opts the subtree into client-side rendering, so Next
 * requires a Suspense boundary above it for the route to keep prerendering
 * its shell (node_modules/next/dist/docs/.../use-search-params.md).
 */
export default function OpportunitiesPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center px-6">
          <p className="text-sm font-semibold text-[var(--muted)]">
            Loading your recommendations...
          </p>
        </main>
      }
    >
      <OpportunitiesList />
    </Suspense>
  );
}
