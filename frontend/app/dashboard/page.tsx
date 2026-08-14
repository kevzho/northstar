"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
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
        <p className="font-mono text-sm text-muted-foreground">
          {checking ? "Checking your profile..." : "Loading Northstar..."}
        </p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6">
        <div className="rounded-lg border bg-card w-full max-w-md p-6 text-center">
          <h1 className="h-display text-3xl text-foreground">
            Sign in required
          </h1>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            You need a Northstar session before opening the dashboard.
          </p>
          <Button render={<Link href="/login" />} className="mt-6 h-11 px-5 font-semibold">
            Go to login
          </Button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <nav className="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/" className="h-display text-xl text-foreground">
            Northstar
          </Link>
          <div className="flex items-center gap-3">
            <Button variant="outline"
              type="button"
              onClick={signOut}
              className="h-10 px-4 font-semibold"
            >
              Sign out
            </Button>
            <ThemeToggle />
          </div>
        </nav>

        <header className="py-10">
          <p className="eyebrow">Signed in</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            Welcome{user.email ? `, ${user.email}` : ""}.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
            Your matches refresh each time you visit — the latest TF-IDF
            scores are always ready below.
          </p>
        </header>

        {/* Recommendations preview — top 4 matches */}
        {matches === null ? (
          <section className="rounded-lg border bg-card mb-10 p-6 text-center">
            <p className="font-mono text-sm text-muted-foreground">
              Fetching your recommendations...
            </p>
          </section>
        ) : matches.length === 0 ? (
          <section className="rounded-lg border bg-card mb-10 p-6 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              No recommendations yet
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Complete onboarding and run the seed data to populate matches.
            </p>
          </section>
        ) : (
          <section className="mb-10">
            <h2 className="h-display text-2xl text-foreground">
              Top matches
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Ranked by opportunity fit — from your TF-IDF profile.
            </p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {(matches.slice(0, 4)).map(({ opportunity, score }) => (
                <Link
                  key={opportunity.id}
                  href={`/opportunities/${opportunity.id}`}
                  className="rounded-lg border bg-card transition-colors hover:border-primary p-4"
                >
                  <span className="badge-fit mb-2">
                    {Math.round(score.score * 100)}% fit
                  </span>
                  <h3 className="text-base font-semibold text-foreground truncate">
                    {opportunity.title}
                  </h3>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground line-clamp-2">
                    {opportunity.blurb}
                  </p>
                  <p className="mt-2 font-mono text-[11px] uppercase tracking-wider text-aurora">
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
            <h2 className="h-display text-2xl text-foreground">
              Your logged outcomes
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
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
                    className="rounded-lg border bg-card flex flex-wrap items-center gap-3 px-4 py-3"
                  >
                    <span className="inline-flex h-6 items-center rounded border border-aurora-dim bg-aurora/10 px-2 font-mono text-xs text-aurora">
                      {outcomeLabels[outcome.status] ?? outcome.status}
                    </span>
                    {match ? (
                      <Link
                        href={`/opportunities/${outcome.opportunity_id}`}
                        className="text-sm font-semibold text-star transition hover:text-star-bright"
                      >
                        {match.opportunity.title}
                      </Link>
                    ) : (
                      <span className="text-sm font-semibold text-foreground">
                        Logged opportunity
                      </span>
                    )}
                    {outcome.impact_notes ? (
                      <span className="text-xs text-muted-foreground">
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
          <Link href="/map" className="rounded-lg border bg-card transition-colors hover:border-primary p-5">
            <h2 className="text-xl font-semibold text-foreground">
              Your pathway map
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              See your matches as a force-directed graph — programs that share a
              field or tags are connected.
            </p>
          </Link>
          <Link href="/opportunities" className="rounded-lg border bg-card transition-colors hover:border-primary p-5">
            <h2 className="text-xl font-semibold text-foreground">
              All recommendations
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              See your full ranked opportunity list with scores and
              explanations.
            </p>
          </Link>
          <Link href="/mentors" className="rounded-lg border bg-card transition-colors hover:border-primary p-5">
            <h2 className="text-xl font-semibold text-foreground">
              Mentor matches
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Mentors ranked by how their expertise lines up with your profile.
            </p>
          </Link>
          <Link href="/onboarding" className="rounded-lg border bg-card transition-colors hover:border-primary p-5">
            <h2 className="text-xl font-semibold text-foreground">
              Edit profile
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Update your interests and goals to refine your match scores.
            </p>
          </Link>
        </section>
      </div>
    </main>
  );
}
