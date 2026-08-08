"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/use-auth";
import { authedFetch, saveStudentProfile, fetchMatches, fetchOutcomes } from "@/lib/api";
import type { MatchResult, Outcome } from "@/lib/types";

const outcomeLabels: Record<Outcome["status"], string> = {
  accepted: "Accepted",
  rejected: "Rejected",
  waitlisted: "Waitlisted",
  withdrew: "Withdrew",
  completed: "Completed",
};

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [checking, setChecking] = useState(false);
  const [matches, setMatches] = useState<MatchResult[] | null>(null);
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);

  // On first sign-in without a profile: create a minimal students row,
  // then redirect to onboarding so the student fills in the real fields.
  useEffect(() => {
    if (loading || !user || checking) return;

    let cancelled = false;
    setChecking(true);

    (async () => {
      try {
        await authedFetch("/me");
        // Profile exists — fetch matches.
        if (!cancelled) {
          setChecking(false);
          try {
            const data = await fetchMatches();
            if (!cancelled) setMatches(data);
          } catch {
            // No catalog yet (no seed data run) — just skip.
            if (!cancelled) setMatches(null);
          }
          try {
            const logged = await fetchOutcomes();
            if (!cancelled) setOutcomes(logged);
          } catch {
            // Outcome history is additive; its absence must not block the page.
            if (!cancelled) setOutcomes([]);
          }
        }
        return;
      } catch {
        // 404 → no profile yet; create a stub then redirect to onboarding.
        try {
          await saveStudentProfile({
            name: null,
            grade: null,
            interests: [],
            goals: null,
            onboarded: false,
          });
        } catch {
          if (!cancelled) setChecking(false);
          return;
        }
      }

      if (!cancelled) {
        setChecking(false);
        router.push("/onboarding");
      }
    })();

    return () => { cancelled = true; };
  }, [loading, user, checking, router]);

  async function signOut() {
    const { supabase } = await import("@/lib/supabase");
    await supabase.auth.signOut();
    window.location.href = "/";
  }

  if (loading || checking) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <p className="text-sm font-semibold text-[var(--muted)]">
          {checking ? "Checking your profile..." : "Loading Northstar..."}
        </p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="w-full max-w-md rounded-lg border border-[var(--border)] bg-[var(--panel)] p-6 text-center shadow-sm">
          <h1 className="text-3xl font-semibold tracking-tight text-[var(--northstar-dark)]">
            Sign in required
          </h1>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
            You need a Northstar session before opening the dashboard.
          </p>
          <Link
            href="/login"
            className="mt-6 inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
          >
            Go to login
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <nav className="flex flex-col gap-4 border-b border-[var(--border)] pb-5 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/"
            className="text-lg font-semibold tracking-tight text-[var(--northstar-dark)]"
          >
            Northstar
          </Link>
          <button
            type="button"
            onClick={signOut}
            className="h-10 rounded-md border border-[var(--border)] bg-[var(--panel)] px-4 text-sm font-semibold text-[var(--northstar-dark)] transition hover:border-[var(--northstar)]"
          >
            Sign out
          </button>
        </nav>

        <header className="py-10">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--amber)]">
            Signed in
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[var(--northstar-dark)]">
            Welcome{user.email ? `, ${user.email}` : ""}.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[var(--muted)]">
            Your matches refresh each time you visit — the latest TF-IDF
            scores are always ready below.
          </p>
        </header>

        {/* Recommendations preview — top 4 matches */}
        {matches === null ? (
          <section className="mb-10 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-6 text-center shadow-sm">
            <p className="text-sm font-semibold text-[var(--muted)]">
              Fetching your recommendations...
            </p>
          </section>
        ) : matches.length === 0 ? (
          <section className="mb-10 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-6 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-[var(--northstar-dark)]">
              No recommendations yet
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              Complete onboarding and run the seed data to populate matches.
            </p>
          </section>
        ) : (
          <section className="mb-10">
            <h2 className="text-lg font-semibold tracking-tight text-[var(--northstar-dark)]">
              Top matches
            </h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Ranked by opportunity fit — from your TF-IDF profile.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {(matches.slice(0, 4)).map(({ opportunity, score }) => (
                <Link
                  key={opportunity.id}
                  href={`/opportunities/${opportunity.id}`}
                  className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-4 shadow-sm transition hover:border-[var(--northstar)]"
                >
                  <div className="mb-2 inline-flex h-6 items-center rounded bg-[var(--northstar)] px-2 text-xs font-semibold text-white">
                    {Math.round(score.score * 100)}%
                  </div>
                  <h3 className="text-base font-semibold text-[var(--foreground)] truncate">
                    {opportunity.title}
                  </h3>
                  <p className="mt-1 text-xs leading-5 text-[var(--muted)] line-clamp-2">
                    {opportunity.blurb}
                  </p>
                  <p className="mt-2 text-[11px] font-medium text-[var(--amber)] uppercase tracking-wider">
                    {opportunity.field} · {opportunity.type}
                  </p>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Outcome history makes the feedback loop visible: each logged result
            fires the migration_004 trigger that re-weights pathway_edges. */}
        {outcomes.length > 0 ? (
          <section className="mb-10">
            <h2 className="text-lg font-semibold tracking-tight text-[var(--northstar-dark)]">
              Your logged outcomes
            </h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Each result you log re-weights the pathway graph behind your
              recommendations.
            </p>
            <ul className="mt-4 grid gap-2">
              {outcomes.slice(0, 5).map((outcome) => {
                const match = matches?.find(
                  (m) => m.opportunity.id === outcome.opportunity_id,
                );
                return (
                  <li
                    key={outcome.id}
                    className="flex flex-wrap items-center gap-3 rounded-md border border-[var(--border)] bg-[var(--panel)] px-4 py-3"
                  >
                    <span className="inline-flex h-6 items-center rounded bg-[var(--amber)] px-2 text-xs font-semibold text-white">
                      {outcomeLabels[outcome.status] ?? outcome.status}
                    </span>
                    {match ? (
                      <Link
                        href={`/opportunities/${outcome.opportunity_id}`}
                        className="text-sm font-semibold text-[var(--northstar-dark)] transition hover:text-[var(--northstar)]"
                      >
                        {match.opportunity.title}
                      </Link>
                    ) : (
                      <span className="text-sm font-semibold text-[var(--foreground)]">
                        Logged opportunity
                      </span>
                    )}
                    {outcome.impact_notes ? (
                      <span className="text-xs text-[var(--muted)]">
                        {outcome.impact_notes}
                      </span>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </section>
        ) : null}

        {/* Every in-app route reachable from one place. /map and /mentors had
            no inbound link anywhere in the app before this — the pathway map is
            the judge-facing centerpiece, so it cannot be URL-only. */}
        <section className="grid gap-4 md:grid-cols-2">
          <Link
            href="/map"
            className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5 shadow-sm transition hover:border-[var(--northstar)]"
          >
            <h2 className="text-xl font-semibold text-[var(--foreground)]">
              Your pathway map
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              See your matches as a force-directed graph — programs that share a
              field or tags are connected.
            </p>
          </Link>
          <Link
            href="/opportunities"
            className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5 shadow-sm transition hover:border-[var(--northstar)]"
          >
            <h2 className="text-xl font-semibold text-[var(--foreground)]">
              All recommendations
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              See your full ranked opportunity list with scores and
              explanations.
            </p>
          </Link>
          <Link
            href="/mentors"
            className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5 shadow-sm transition hover:border-[var(--northstar)]"
          >
            <h2 className="text-xl font-semibold text-[var(--foreground)]">
              Mentor matches
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              Mentors ranked by how their expertise lines up with your profile.
            </p>
          </Link>
          <Link
            href="/onboarding"
            className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5 shadow-sm transition hover:border-[var(--northstar)]"
          >
            <h2 className="text-xl font-semibold text-[var(--foreground)]">
              Edit profile
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              Update your interests and goals to refine your match scores.
            </p>
          </Link>
        </section>
      </div>
    </main>
  );
}
