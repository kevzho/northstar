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
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";
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
        <div className="flex items-center justify-between border-b border-border pb-5">
          <Link
            href="/dashboard"
            className="h-display text-xl text-foreground"
          >
            Northstar
          </Link>
          <Link
            href="/dashboard"
            className="text-sm font-semibold text-aurora"
          >
            Back to dashboard
          </Link>
        </div>

        <header className="mt-10">
          <p className="eyebrow">Recommendations</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            Opportunities for you
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
            Ranked by the Northstar TF-IDF match engine against your profile.
            Filter by field and type to focus the list.
          </p>
        </header>

        <section className="mt-6 flex flex-wrap gap-3">
          <NativeSelect
            value={field}
            aria-label="Filter by field"
            onChange={(event) => setFilter("field", event.target.value)}
            className="h-11 px-4 font-semibold"
          >
            {fieldFilters.map((filter) => (
              <option key={filter.value} value={filter.value}>
                {filter.label}
              </option>
            ))}
          </NativeSelect>
          <NativeSelect
            value={type}
            aria-label="Filter by type"
            onChange={(event) => setFilter("type", event.target.value)}
            className="h-11 px-4 font-semibold"
          >
            {typeFilters.map((filter) => (
              <option key={filter.value} value={filter.value}>
                {filter.label}
              </option>
            ))}
          </NativeSelect>
        </section>

        {filtered.length > 0 ? (
          <section className="mt-8 grid gap-4 md:grid-cols-2">
            {filtered.map(({ opportunity, score }) => (
              <div key={opportunity.id} className="grid gap-2">
                <OpportunityCard opportunity={opportunity} />
                <p className="px-1 text-xs text-muted-foreground">
                  <span className="font-mono text-star">
                    {Math.round(score.score * 100)}% fit
                  </span>{" "}
                  · {score.explanation}
                </p>
              </div>
            ))}
          </section>
        ) : matches.length > 0 ? (
          // Results exist but the current filters exclude all of them. Saying
          // "finish onboarding" here would send the student down the wrong path.
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              Nothing matches these filters
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              You have {matches.length} ranked{" "}
              {matches.length === 1 ? "opportunity" : "opportunities"}, but none
              in this field and type combination.
            </p>
            <Button
              onClick={() => router.replace(pathname, { scroll: false })}
              className="mt-6 h-11 px-5 font-semibold"
            >
              Clear filters
            </Button>
          </section>
        ) : (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              No recommendations yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Take the 5-minute assessment or finish onboarding so the match
              engine has a profile to rank from.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Button render={<Link href="/onboarding" />} className="h-11 px-5 font-semibold">
                Finish onboarding
              </Button>
              <Button variant="outline" render={<Link href="/assessment" />} className="h-11 px-5 font-semibold">
                Take assessment
              </Button>
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
          <p className="font-mono text-sm text-muted-foreground">
            Loading your recommendations...
          </p>
        </main>
      }
    >
      <OpportunitiesList />
    </Suspense>
  );
}
