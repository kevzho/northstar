"use client";

/**
 * Opportunity list page.
 *
 * Lists the student's matched opportunities with filters by field and type.
 * Data is fetched through lib/api.fetchMatches() which calls GET /match on
 * the FastAPI backend. The page renders score + explanation under each card
 * and falls through to an empty state when no matches exist.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
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

export default function OpportunitiesPage() {
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [field, setField] = useState<OpportunityField | "all">("all");
  const [type, setType] = useState<OpportunityType | "all">("all");

  useEffect(() => {
    let mounted = true;
    fetchMatches()
      .then((result) => {
        if (mounted) setMatches(result);
      })
      .catch(() => {
        // Stub returns []; future backend errors fall through to the empty
        // state below. The decoder never re-throws here today.
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
            Meridian
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
            Ranked by the Meridian TF-IDF match engine against your profile.
            Filter by field and type to focus the list.
          </p>
        </header>

        <section className="mt-6 flex flex-wrap gap-3">
          <select
            value={field}
            onChange={(event) => setField(event.target.value as OpportunityField | "all")}
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
            onChange={(event) => setType(event.target.value as OpportunityType | "all")}
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
