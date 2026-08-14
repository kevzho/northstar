"use client";

/**
 * Future paths.
 *
 * Previously this took `archetypes.slice(0, 3)` and labelled them safe /
 * ambitious / unconventional in array order — the same three for everyone. The
 * paths are now selected against the student's trait vector by
 * lib/scoring.ts#selectFuturePaths, and every archetype shows its fit score.
 */

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { archetypes } from "@/lib/archetypes";
import {
  pathLabel,
  rankArchetypes,
  scoreTraits,
  selectFuturePaths,
} from "@/lib/scoring";
import { useStoredAnswers } from "@/lib/use-assessment";

export default function FuturesPage() {
  const answers = useStoredAnswers();
  const traits = answers ? scoreTraits(answers) : null;
  const paths = traits ? selectFuturePaths(traits) : null;
  const ranked = traits ? rankArchetypes(traits) : null;

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
          <Button render={<Link href="/plan" />} className="h-11 shrink-0 px-5 font-semibold">
            Choose a path
          </Button>
        </header>

        {paths === null ? (
          <section className="rounded-lg border bg-card mt-8 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              No trait profile yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Future paths are ranked against your six trait scores. Take the
              eight-question assessment first — it takes about five minutes.
            </p>
            <Button render={<Link href="/assessment" />} className="mt-6 h-11 px-5 font-semibold">
              Take the assessment
            </Button>
          </section>
        ) : (
          <section className="mt-8 grid gap-4 lg:grid-cols-3">
            {paths.map((path) => (
              <article key={path.archetype.id} className="rounded-lg border bg-card flex flex-col p-5">
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
              </article>
            ))}
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
