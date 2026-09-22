"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AppNav } from "@/components/AppNav";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/use-auth";
import { authedFetch, fetchMatches, fetchOutcomes, isApiError } from "@/lib/api";
import { traitLabels } from "@/lib/assessment";
import { TRAIT_KEYS, scoreTraits } from "@/lib/scoring";
import { useStoredAnswers } from "@/lib/use-assessment";
import type { MatchResult, Outcome } from "@/lib/types";
import { LoadingScreen } from "@/components/decor/orbit-loader";

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
  const [studentName, setStudentName] = useState<string | null>(null);
  const [matches, setMatches] = useState<MatchResult[] | null>(null);
  const [matchesFailed, setMatchesFailed] = useState(false);
  const [profileFailed, setProfileFailed] = useState(false);
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);
  const answers = useStoredAnswers();

  // On first sign-in without a profile: send the student to onboarding.
  //
  // This used to POST a stub row {name:null, grade:null, interests:[],
  // goals:null, onboarded:false} BEFORE redirecting, which was a one-way
  // trap. Once that row existed GET /me returned 200 forever, so a student
  // who closed the tab on the onboarding form came back to a dashboard that
  // took its success branch, ran the matcher against an empty profile
  // (_query_for_student tokenizes to nothing), and showed them an empty list
  // on every request from then on. Taking the assessment did not help:
  // POST /assessment-profile writes columns the matcher never reads.
  //
  // The fix is to read the `onboarded` flag the app already writes in three
  // places and had never once read, and to stop creating the row early --
  // POST /students at the end of onboarding upserts it anyway.
  //
  // The run-once guard is a ref, NOT the `checking` state: `checking` in
  // the dependency array meant setChecking(true) re-ran the effect and
  // fired the cleanup, so `cancelled` flipped before the fetch resolved
  // and no completion path could ever clear the spinner.
  const startedCheck = useRef(false);
  useEffect(() => {
    if (loading || !user || startedCheck.current) return;
    startedCheck.current = true;

    let cancelled = false;
    setChecking(true);

    (async () => {
      try {
        const me = await (await authedFetch("/me")).json();

        // A row can exist without onboarding being finished — an account
        // created before this check, or a future partial-save path. Trust
        // the flag, not the row's existence.
        if (me?.onboarded !== true) {
          if (!cancelled) {
            setChecking(false);
            router.push("/onboarding");
          }
          return;
        }

        // Profile exists and is complete — greet by name, fetch matches.
        if (!cancelled) {
          setStudentName((me?.name ?? "").trim() || null);
          setChecking(false);
          try {
            const data = await fetchMatches();
            if (!cancelled) setMatches(data);
          } catch {
            // Failure is not emptiness — the page says so instead of
            // showing a permanent spinner.
            if (!cancelled) {
              setMatches(null);
              setMatchesFailed(true);
            }
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
      } catch (err) {
        if (cancelled) return;
        setChecking(false);
        // 404 is the only status that means "no profile yet." A 500, a
        // dropped connection or an expired session is a failure to ANSWER
        // the question, and must not be read as an answer — the old code
        // caught all of them and wrote a stub row in response.
        if (isApiError(err) && err.status === 404) {
          router.push("/onboarding");
        } else {
          setProfileFailed(true);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [loading, user, router]);

  async function signOut() {
    const { supabase } = await import("@/lib/supabase");
    await supabase.auth.signOut();
    window.location.href = "/";
  }

  if (loading || checking) {
    return (
      <LoadingScreen
        label={checking ? "Reading your charts..." : "Bringing the sky into focus..."}
      />
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

  // --- Today strip inputs -------------------------------------------------
  const closingSoon = (matches ?? [])
    .map(({ opportunity }) => {
      if (!opportunity.deadline) return null;
      const due = new Date(`${opportunity.deadline}T23:59:59`).getTime();
      if (Number.isNaN(due)) return null;
      const days = Math.ceil((due - Date.now()) / 86_400_000);
      return days >= 0 && days <= 30 ? { opportunity, days } : null;
    })
    .filter((entry): entry is NonNullable<typeof entry> => entry !== null)
    .sort((a, b) => a.days - b.days)
    .slice(0, 3);

  const traitScores = answers ? scoreTraits(answers) : null;
  const strongestTrait = traitScores
    ? (() => {
        const top = [...TRAIT_KEYS].sort(
          (a, b) => traitScores[b] - traitScores[a],
        )[0];
        return { label: traitLabels[top], score: traitScores[top] };
      })()
    : null;

  const nextAction = !answers
    ? {
        href: "/assessment",
        label: "Take the assessment",
        blurb: "Fourteen prompts build the profile everything else runs on.",
      }
    : outcomes.length === 0
      ? {
          href: "/opportunities",
          label: "Find one to pursue",
          blurb:
            "Bookmark an opportunity and log its outcome — every result you log sharpens your rankings.",
        }
      : {
          href: "/plan",
          label: "Review your plan",
          blurb: "Your 30-day plan updates with your profile and matches.",
        };

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <AppNav
          right={
            <Button variant="outline"
              type="button"
              onClick={signOut}
              className="h-10 px-4 font-semibold"
            >
              Sign out
            </Button>
          }
        />

        <header className="py-10">
          <p className="eyebrow">Mission control</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            Welcome{studentName ? `, ${studentName.split(" ")[0]}` : ""}.
          </h1>
          {!studentName ? (
            <p className="mt-2 text-sm text-muted-foreground">
              Northstar doesn&apos;t know your name yet —{" "}
              <Link href="/profile" className="font-semibold text-aurora">
                add it to your profile
              </Link>
              .
            </p>
          ) : null}
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
            Your matches refresh each time you visit — the latest TF-IDF
            scores are always ready below.
          </p>
        </header>

        {/* Today strip: proof the product knows you, before anything else. */}
        <section className="mb-10 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-lg border bg-card p-5">
            <p className="eyebrow">Closing soon</p>
            {closingSoon.length > 0 ? (
              <ul className="mt-3 grid gap-2">
                {closingSoon.map(({ opportunity, days }) => (
                  <li
                    key={opportunity.id}
                    className="flex min-w-0 items-baseline justify-between gap-3"
                  >
                    <Link
                      href={`/opportunities/${opportunity.id}`}
                      title={opportunity.title}
                      className="min-w-0 truncate text-sm font-semibold text-foreground hover:underline"
                    >
                      {opportunity.title}
                    </Link>
                    <span className="shrink-0 font-mono text-xs text-star">
                      {days === 0 ? "today" : `${days}d`}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                No deadlines in the next 30 days.
              </p>
            )}
          </div>
          <div className="rounded-lg border bg-card p-5">
            <p className="eyebrow">Strongest signal</p>
            {strongestTrait ? (
              <>
                <p className="mt-3 text-2xl font-semibold text-foreground">
                  {strongestTrait.label}
                </p>
                <p className="mt-1 font-mono text-sm text-star">
                  {strongestTrait.score}/100
                </p>
              </>
            ) : (
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Take the assessment to see your trait profile here.
              </p>
            )}
          </div>
          <div className="rounded-lg border bg-card p-5">
            <p className="eyebrow">Next action</p>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              {nextAction.blurb}
            </p>
            <Button render={<Link href={nextAction.href} />} className="mt-4 h-10 px-4">
              {nextAction.label}
            </Button>
          </div>
        </section>

        {/* Recommendations preview — top 4 matches */}
        {profileFailed ? (
          <section className="rounded-lg border border-destructive/40 bg-card mb-10 p-6 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              Could not load your profile
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Your account is fine — we just could not reach the server.
              Reload in a moment.
            </p>
          </section>
        ) : matchesFailed ? (
          <section className="rounded-lg border border-destructive/40 bg-card mb-10 p-6 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              Could not reach the match engine
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              This is a connection problem, not an empty list — retry in a
              moment.
            </p>
          </section>
        ) : matches === null ? (
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
              Nothing in the catalog matches your profile yet. Adding a couple
              more interests usually fixes it — the matcher reads those
              directly.
            </p>
            <Button
              render={<Link href="/profile" />}
              className="mt-4 h-10 px-4"
            >
              Edit your interests
            </Button>
          </section>
        ) : (
          <section className="mb-10">
            <h2 className="h-display text-2xl text-foreground">
              Top matches
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Ranked by opportunity fit — from your TF-IDF profile.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {(matches.slice(0, 4)).map(({ opportunity, score }) => (
                <Link
                  key={opportunity.id}
                  href={`/opportunities/${opportunity.id}`}
                  className="min-w-0 rounded-lg border bg-card transition-colors hover:border-primary p-4"
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
          <Link href="/projects" className="rounded-lg border bg-card transition-colors hover:border-primary p-5">
            <h2 className="text-xl font-semibold text-foreground">
              Projects to join
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Real open-source repos in your fields with good first issues
              open right now.
            </p>
          </Link>
          <Link href="/discover" className="rounded-lg border bg-card transition-colors hover:border-primary p-5">
            <h2 className="text-xl font-semibold text-foreground">
              Find your people
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Discover students who share your fields and path, then compare
              records side by side.
            </p>
          </Link>
          <Link href="/teamup" className="rounded-lg border bg-card transition-colors hover:border-primary p-5">
            <h2 className="text-xl font-semibold text-foreground">
              Team up
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Find a collaborator or study buddy — pick who you&apos;d build
              with, connect only when it&apos;s mutual.
            </p>
          </Link>
          <Link href="/advisor" className="rounded-lg border bg-card transition-colors hover:border-primary p-5">
            <h2 className="text-xl font-semibold text-foreground">
              Explore unusual routes
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Ask about directions the rankings can&apos;t see — answers
              grounded in your verified matches.
            </p>
          </Link>
          <Link href="/profile" className="rounded-lg border bg-card transition-colors hover:border-primary p-5">
            <h2 className="text-xl font-semibold text-foreground">
              Edit profile
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              All your details, traits, and sharing settings on one page —
              edit anything to refine your matches.
            </p>
          </Link>
        </section>
      </div>
    </main>
  );
}
