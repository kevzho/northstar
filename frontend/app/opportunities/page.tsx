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
import { AppNav } from "@/components/AppNav";
import { NativeSelect } from "@/components/ui/native-select";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { OpportunityCard } from "@/components/OpportunityCard";
import { dismissOpportunity, fetchCatalog, fetchMatches, undoDismissal } from "@/lib/api";
import type { MatchResult, Opportunity, OpportunityField, OpportunityType } from "@/lib/types";
import { LoadingScreen, LoadingSection } from "@/components/decor/orbit-loader";

const fieldFilters: { value: OpportunityField | "all"; label: string }[] = [
  { value: "all", label: "All fields" },
  { value: "cs", label: "Computer Science" },
  { value: "biology", label: "Biology" },
  { value: "math", label: "Math" },
  { value: "physics", label: "Physics" },
  { value: "engineering", label: "Engineering" },
  { value: "interdisciplinary", label: "Interdisciplinary" },
  { value: "design", label: "Design & Media" },
  { value: "business", label: "Business" },
  { value: "humanities", label: "Humanities" },
  { value: "health", label: "Health" },
];

const typeFilters: { value: OpportunityType | "all"; label: string }[] = [
  { value: "all", label: "All types" },
  { value: "program", label: "Programs" },
  { value: "scholarship", label: "Scholarships" },
  { value: "competition", label: "Competitions" },
  { value: "mentorship", label: "Mentorship" },
  { value: "internship", label: "Internships" },
  { value: "volunteer", label: "Volunteer" },
  { value: "journal", label: "Journals" },
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
  const [loadFailed, setLoadFailed] = useState(false);
  // Ids dismissed this session, newest last — drives the undo strip.
  const [dismissedHere, setDismissedHere] = useState<string[]>([]);
  const [catalog, setCatalog] = useState<Opportunity[] | null>(null);
  const view = searchParams.get("view") === "all" ? "all" : "matched";
  const cost = searchParams.get("cost") === "free" ? "free"
    : searchParams.get("cost") === "paid" ? "paid" : "all";
  const status = searchParams.get("status") === "open" ? "open"
    : searchParams.get("status") === "closing" ? "closing" : "all";

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

  // Captured once via the lazy initializer: render must stay pure
  // (react-hooks/purity forbids a bare Date.now() there), and deadline
  // math is day-granular, so one timestamp per mount is plenty.
  const [now] = useState(() => Date.now());

  function setFilter(key: "field" | "type" | "cost" | "status", value: string) {
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
        if (mounted) {
          setMatches(result);
          setLoadFailed(false);
        }
      })
      .catch(() => {
        // Failure is not emptiness: an unreachable backend or missing
        // profile renders an honest error card, never "no matches".
        if (mounted) {
          setMatches([]);
          setLoadFailed(true);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  function dismiss(opportunityId: string) {
    setDismissedHere((current) => [...current, opportunityId]);
    dismissOpportunity(opportunityId).catch(() =>
      setDismissedHere((current) => current.filter((id) => id !== opportunityId)),
    );
  }

  function undoLastDismiss() {
    const last = dismissedHere[dismissedHere.length - 1];
    if (!last) return;
    setDismissedHere((current) => current.slice(0, -1));
    undoDismissal(last).catch(() => {});
  }

  useEffect(() => {
    if (view !== "all" || catalog !== null) return;
    let mounted = true;
    fetchCatalog()
      .then((rows) => {
        if (mounted) setCatalog(rows);
      })
      .catch(() => {
        if (mounted) setCatalog([]);
      });
    return () => {
      mounted = false;
    };
  }, [view, catalog]);

  function setView(next: "matched" | "all") {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "all") params.set("view", "all");
    else params.delete("view");
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  function passesCostStatus(o: {
    cost?: number | null;
    deadline?: string | null;
  }): boolean {
    if (cost === "free" && (o.cost ?? 0) > 0) return false;
    if (cost === "paid" && (o.cost ?? 0) === 0) return false;
    if (status !== "all") {
      if (!o.deadline) return status === "open" ? true : false;
      const days = Math.ceil(
        (new Date(`${o.deadline}T23:59:59`).getTime() - now) / 86_400_000,
      );
      if (status === "open" && days < 0) return false;
      if (status === "closing" && (days < 0 || days > 30)) return false;
    }
    return true;
  }

  const filtered = matches.filter(({ opportunity }) => {
    if (dismissedHere.includes(opportunity.id)) return false;
    if (field !== "all" && opportunity.field !== field) return false;
    if (type !== "all" && opportunity.type !== type) return false;
    if (!passesCostStatus(opportunity)) return false;
    return true;
  });

  const filteredCatalog = (catalog ?? []).filter((opportunity) => {
    if (field !== "all" && opportunity.field !== field) return false;
    if (type !== "all" && opportunity.type !== type) return false;
    if (!passesCostStatus(opportunity)) return false;
    return true;
  });

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <AppNav
          homeHref="/dashboard"
          right={
            <Link
              href="/dashboard"
              className="text-sm font-semibold text-aurora"
            >
              Back to dashboard
            </Link>
          }
        />

        <header className="mt-10">
          <p className="eyebrow">Opportunities</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            {view === "all" ? "The full bank" : "Opportunities for you"}
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
            {view === "all"
              ? "Every opportunity in the catalog, sorted by deadline. Switch back to Matched to see them ranked for your profile."
              : "Ranked by the Northstar match engine against your profile. Or browse the entire bank."}
          </p>
          <div className="mt-5 inline-flex border border-border">
            <button
              type="button"
              onClick={() => setView("matched")}
              className={
                view === "matched"
                  ? "bg-foreground px-4 py-2 text-sm font-medium text-background"
                  : "bg-transparent px-4 py-2 text-sm font-medium text-foreground"
              }
            >
              Matched for you
            </button>
            <button
              type="button"
              onClick={() => setView("all")}
              className={
                view === "all"
                  ? "bg-foreground px-4 py-2 text-sm font-medium text-background"
                  : "bg-transparent px-4 py-2 text-sm font-medium text-foreground"
              }
            >
              Browse all
            </button>
          </div>
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
          <NativeSelect
            value={cost}
            aria-label="Filter by cost"
            onChange={(event) => setFilter("cost", event.target.value)}
            className="h-11 px-4 font-semibold"
          >
            <option value="all">Any cost</option>
            <option value="free">Free only</option>
            <option value="paid">Paid</option>
          </NativeSelect>
          <NativeSelect
            value={status}
            aria-label="Filter by status"
            onChange={(event) => setFilter("status", event.target.value)}
            className="h-11 px-4 font-semibold"
          >
            <option value="all">Any status</option>
            <option value="open">Open now</option>
            <option value="closing">Closing in 30 days</option>
          </NativeSelect>
        </section>

        {dismissedHere.length > 0 ? (
          <p className="mt-4 text-sm text-muted-foreground">
            {dismissedHere.length} marked not for you — future rankings skip
            {dismissedHere.length === 1 ? " it" : " them"}.{" "}
            <button
              type="button"
              onClick={undoLastDismiss}
              className="font-semibold text-star underline underline-offset-4"
            >
              Undo last
            </button>
          </p>
        ) : null}

        {view === "all" ? (
          catalog === null ? (
            <LoadingSection label="Loading the full bank..." />
          ) : filteredCatalog.length > 0 ? (
            <>
              <p className="mt-6 font-mono text-xs text-muted-foreground">
                {filteredCatalog.length} opportunit
                {filteredCatalog.length === 1 ? "y" : "ies"} in the catalog
              </p>
              <section className="mt-4 grid gap-4 md:grid-cols-2">
                {filteredCatalog.map((opportunity) => (
                  <OpportunityCard key={opportunity.id} opportunity={opportunity} />
                ))}
              </section>
            </>
          ) : (
            <section className="rounded-lg border bg-card mt-10 p-8 text-center">
              <h2 className="text-xl font-semibold text-foreground">
                Nothing in the catalog matches these filters
              </h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Try clearing the field or type filter.
              </p>
            </section>
          )
        ) : loadFailed ? (
          <section className="rounded-lg border border-destructive/40 bg-card mt-10 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              Could not load your recommendations
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              The Northstar backend did not answer — this is a connection
              problem, not an empty list. Sign in again or retry.
            </p>
            <Button
              onClick={() => window.location.reload()}
              className="mt-6 h-11 px-5 font-semibold"
            >
              Retry
            </Button>
          </section>
        ) : filtered.length > 0 ? (
          <section className="mt-8 grid gap-4 md:grid-cols-2">
            {filtered.map(({ opportunity, score }) => (
              <div key={opportunity.id} className="grid gap-2">
                <OpportunityCard
                  opportunity={opportunity}
                  onDismiss={() => dismiss(opportunity.id)}
                />
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
      fallback={<LoadingScreen label="Loading your recommendations..." />}
    >
      <OpportunitiesList />
    </Suspense>
  );
}
