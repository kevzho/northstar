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
import { ThemeToggle } from "@/components/theme-toggle";
import { archetypes } from "@/lib/archetypes";
import { authedFetch, syncChosenPath } from "@/lib/api";
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

const emptySubscribe = () => () => {};

export default function FuturesPage() {
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

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Link
              href="/profile"
              className="text-sm font-semibold text-aurora"
            >
              Back to profile
            </Link>
            <h1 className="h-display mt-3 text-4xl text-foreground">
              Future paths
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
              Northstar compares the trait profile to archetypes and returns
              three paths: one steady, one stretch, and one surprising but
              plausible direction.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <Button render={<Link href="/plan" />} className="h-11 px-5 font-semibold">
              Choose a path
            </Button>
            <ThemeToggle />
          </div>
        </header>

        {!hydrated ? (
          <LoadingSection label="Reading your trait chart..." className="mt-8 flex flex-col items-center gap-4 py-10 text-center" />
        ) : paths === null ? (
          <section className="rounded-lg border bg-card mt-8 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
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
          </section>
        )}

        <section className="rounded-lg border bg-card mt-8 p-5">
          <h2 className="h-display text-2xl text-foreground">
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
