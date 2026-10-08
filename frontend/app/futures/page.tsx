"use client";

/**
 * Future paths.
 *
 * Previously this took `archetypes.slice(0, 3)` and labelled them safe /
 * ambitious / unconventional in array order — the same three for everyone. The
 * paths are now selected against the student's trait vector by
 * lib/scoring.ts#selectFuturePaths, and every archetype shows its fit score.
 */

import { useEffect, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { archetypes } from "@/lib/archetypes";
import { authedFetch, regenerateSpine, syncChosenPath } from "@/lib/api";
import {
  interestFields,
  leadingFields,
  pathLabel,
  rankArchetypes,
  scoreFieldInterests,
  scoreTraits,
  selectFuturePaths,
  type FuturePath,
} from "@/lib/scoring";
import type { OpportunityField, StudentProfile } from "@/lib/types";
import { useStoredAnswers } from "@/lib/use-assessment";
import { useChosenPath, writeChosenPath } from "@/lib/use-chosen-path";
import { LoadingSection } from "@/components/decor/orbit-loader";
import { useRequireAuth } from "@/lib/use-require-auth";
import { AppNav } from "@/components/AppNav";

const emptySubscribe = () => () => {};

export default function FuturesPage() {
  // Built from this student's own assessment, so it needs an account.
  // Signed out this used to render a heading and an empty shell while the
  // API answered 401 — gated and broken look identical from there.
  useRequireAuth();
  const router = useRouter();
  const answers = useStoredAnswers();
  const chosen = useChosenPath();
  // Signed-in interests personalize the ranking (small field bonus in
  // lib/scoring.ts); signed out, ranking is traits-only.
  const [fields, setFields] = useState<OpportunityField[]>([]);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await authedFetch("/me");
        const me = (await response.json()) as StudentProfile;
        if (!cancelled) setFields(interestFields(me.interests ?? []));
      } catch {
        // Signed out — traits-only ranking.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);
  const traits = answers ? scoreTraits(answers) : null;
  // Stated interests (onboarding) plus what the quiz's field-signal
  // questions revealed — union, so neither source can erase the other.
  const quizFields = answers ? leadingFields(scoreFieldInterests(answers)) : [];
  const allFields = [...new Set([...fields, ...quizFields])];
  const paths = traits ? selectFuturePaths(traits, allFields) : null;
  // Stored answers are always null during the server render; only after
  // hydration does null mean "never took the quiz", so a student WITH a
  // profile never sees the empty state flash.
  const hydrated = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
  const ranked = traits ? rankArchetypes(traits, allFields) : null;

  function chart(path: FuturePath) {
    writeChosenPath({ archetypeId: path.archetype.id, kind: path.kind });
    // Best-effort server sync so friends can compare career choices.
    syncChosenPath(path.archetype.id, path.kind).catch(() => {});
    router.push("/plan");
  }

  const [broadening, setBroadening] = useState(false);
  const [broadError, setBroadError] = useState("");

  /**
   * "None of these are me."
   *
   * Picking a profession at fifteen is a bigger commitment than this page was
   * admitting, and a student who does not see themselves in three archetypes
   * was previously stuck: no path charted means no spine, which means a
   * roadmap with no build or publish step at all.
   *
   * So declining produces a plan instead of a dead end. The model writes a
   * spine from what the student actually has — their traits, grade, fields and
   * real matched opportunities — and uses the archetype only as context it can
   * do without. No career label is stored.
   */
  async function goBroad() {
    setBroadening(true);
    setBroadError("");
    writeChosenPath({ archetypeId: "", kind: "broad" });
    syncChosenPath("", "broad").catch(() => {});
    try {
      await regenerateSpine(
        "I do not see myself in any of the suggested career paths. My interests " +
        "are broader than one profession — give me a plan for the areas I am " +
        "actually interested in, not a job title.",
      );
    } catch (caught) {
      // Swallowing this sent a student to a plan with no build or publish step
      // and nothing saying why. Every refusal from that endpoint is one they
      // should read — out of budget, model unreachable, or a path that came
      // back pointing at a skill with nothing behind it — and in all three
      // their matched opportunities and deadlines are still waiting on /plan,
      // so the offer is to continue rather than a dead end.
      setBroadening(false);
      setBroadError(
        caught instanceof Error
          ? caught.message
          : "Could not write your plan just now.",
      );
      return;
    }
    router.push("/plan");
  }

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <AppNav homeHref="/dashboard"
          right={
            <>
              <Button render={<Link href="/plan" />} className="h-11 px-5 font-semibold">
                Choose a path
              </Button>
            </>
          }
         />

        <header className="pb-6">
            <Link
              href="/profile"
              className="text-sm font-semibold text-aurora"
            >
              Back to profile
            </Link>
            <h1 className="h-display mt-3 text-title text-foreground">
              Future paths
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
              Northstar compares the trait profile to archetypes and returns
              three paths: one steady, one stretch, and one surprising but
              plausible direction.
            </p>
        </header>

        {!hydrated ? (
          <LoadingSection label="Reading your trait chart..." className="mt-8 flex flex-col items-center gap-4 py-10 text-center" />
        ) : paths === null ? (
          <section className="rounded-lg border bg-card mt-8 p-8 text-center">
            <h2 className="h-display text-section text-foreground">
              No trait profile yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Future paths are ranked against your six trait scores. Take the
              twenty-question assessment first — it takes about five minutes.
            </p>
            <Button render={<Link href="/assessment" />} className="mt-6 h-11 px-5 font-semibold">
              Take the assessment
            </Button>
          </section>
        ) : (
          <section className="mt-8 grid gap-4 lg:grid-cols-3">
            {paths.map((path) => {
              const isCharted = chosen?.archetypeId === path.archetype.id;
              return (
                <article
                  key={path.archetype.id}
                  className={`flex flex-col rounded-lg border bg-card p-5 ${
                    isCharted ? "border-star" : ""
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="eyebrow">{pathLabel(path.kind)}</p>
                    <span className="badge-fit">{path.fit}% fit</span>
                  </div>
                  <h2 className="h-display mt-3 text-3xl text-foreground">
                    {path.archetype.label}
                  </h2>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground">
                    {path.archetype.summary}
                  </p>
                  {/* What a path actually looks like, because "Quantitative
                      Economist" is a job title and a 15-year-old cannot accept
                      or reject one. Collapsed so the card stays scannable. */}
                  {path.archetype.examples?.length ? (
                    <details className="mt-4 group">
                      <summary className="cursor-pointer text-note font-medium text-foreground marker:text-aurora">
                        What that actually looks like
                      </summary>
                      <ul className="mt-2 space-y-1.5">
                        {path.archetype.examples.map((example) => (
                          <li
                            key={example}
                            className="flex gap-2 text-xs leading-5 text-muted-foreground"
                          >
                            <span aria-hidden="true" className="text-aurora">—</span>
                            <span>{example}</span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                  <p className="mt-4 text-xs leading-5 text-aurora italic">
                    {path.rationale}
                  </p>
                  <div className="mt-auto pt-5">
                    <Button
                      variant={isCharted ? "default" : "outline"}
                      onClick={() => chart(path)}
                      className="h-10 w-full font-semibold"
                    >
                      {isCharted ? "Charted — see your plan" : "Chart this path"}
                    </Button>
                  </div>
                </article>
              );
            })}

            {/*
              The exit. Three archetypes is a suggestion, not a census, and a
              student who does not recognise themselves in any of them used to
              have nowhere to go: no charted path means no spine, which means a
              roadmap with no build or publish step at all.

              Deliberately the same visual weight as a path card rather than a
              small link underneath. "None of these" is a legitimate answer to
              this question, and burying it tells a student their reaction was
              the wrong one.
            */}
            <article className="flex flex-col rounded-lg border border-dashed border-border bg-transparent p-5">
              <p className="eyebrow">Or</p>
              <h2 className="h-display mt-3 text-section text-foreground">
                None of these are me
              </h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Picking a profession at your age is a big commitment, and you do
                not have to make one here. A path is a starting direction, not a
                decision — and if none of these three fit, the honest answer is
                that your interests are broader than one job title.
              </p>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Choose this and the plan is built from what you actually have:
                your six signals, your grade, the fields you lean toward, and
                the opportunities open to you now. No career label is stored.
              </p>
              <div className="mt-auto pt-5">
                <Button
                  variant="outline"
                  onClick={goBroad}
                  disabled={broadening}
                  className="h-10 w-full font-semibold"
                >
                  {broadening ? "Writing your plan…" : "My interests are broader"}
                </Button>
                {broadError ? (
                  <p aria-live="polite" className="mt-3 text-note leading-6 text-foreground">
                    {broadError}{" "}
                    <Link href="/plan" className="underline">
                      Go to your plan anyway
                    </Link>{" "}
                    — your matched opportunities and their deadlines are there,
                    and you can ask for the written part again from that page.
                  </p>
                ) : null}
              </div>
            </article>
          </section>
        )}

        <section className="rounded-lg border bg-card mt-8 p-5">
          <h2 className="h-display text-section text-foreground">
            Archetype library
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {ranked
              ? "Every archetype, scored against your trait profile."
              : "The full set Northstar ranks against."}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {(ranked ?? archetypes.map((a) => ({ archetype: a, fit: null }))).map(
              (entry) => (
                <div
                  key={entry.archetype.id}
                  className="rounded-md border border-border bg-panel-raised p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="font-semibold text-foreground">
                      {entry.archetype.label}
                    </p>
                    {entry.fit !== null ? (
                      <span className="shrink-0 font-mono text-xs text-star">
                        {entry.fit}%
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {entry.archetype.summary}
                  </p>
                </div>
              ),
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
