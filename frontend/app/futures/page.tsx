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
        <header className="flex flex-col gap-4 border-b border-[var(--border)] pb-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Link
              href="/profile"
              className="text-sm font-semibold text-[var(--northstar)]"
            >
              Back to profile
            </Link>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[var(--northstar-dark)]">
              Future Paths
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--muted)]">
              Northstar compares the trait profile to archetypes and returns
              three paths: one steady, one stretch, and one surprising but
              plausible direction.
            </p>
          </div>
          <Link
            href="/plan"
            className="inline-flex h-11 shrink-0 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
          >
            Choose a path
          </Link>
        </header>

        {paths === null ? (
          <section className="mt-8 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-8 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-[var(--northstar-dark)]">
              No trait profile yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              Future paths are ranked against your six trait scores. Take the
              eight-question assessment first — it takes about five minutes.
            </p>
            <Link
              href="/assessment"
              className="mt-6 inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
            >
              Take the assessment
            </Link>
          </section>
        ) : (
          <section className="mt-8 grid gap-4 lg:grid-cols-3">
            {paths.map((path) => (
              <article
                key={path.archetype.id}
                className="flex flex-col rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5 shadow-sm"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-[var(--amber)]">
                    {pathLabel(path.kind)}
                  </p>
                  <span className="inline-flex h-6 items-center rounded bg-[var(--northstar)] px-2 text-xs font-semibold text-white">
                    {path.fit}% fit
                  </span>
                </div>
                <h2 className="mt-3 text-2xl font-semibold tracking-tight text-[var(--foreground)]">
                  {path.archetype.label}
                </h2>
                <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
                  {path.archetype.summary}
                </p>
                <p className="mt-4 text-xs leading-5 text-[var(--northstar-dark)] italic">
                  {path.rationale}
                </p>
              </article>
            ))}
          </section>
        )}

        <section className="mt-8 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">
            Archetype library
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {ranked
              ? "Every archetype, scored against your trait profile."
              : "The full set Northstar ranks against."}
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {(ranked ?? archetypes.map((a) => ({ archetype: a, fit: null }))).map(
              (entry) => (
                <div
                  key={entry.archetype.id}
                  className="rounded-md border border-[var(--border)] bg-white/70 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="font-semibold text-[var(--northstar-dark)]">
                      {entry.archetype.label}
                    </p>
                    {entry.fit !== null ? (
                      <span className="shrink-0 text-xs font-semibold text-[var(--northstar)]">
                        {entry.fit}%
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
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
