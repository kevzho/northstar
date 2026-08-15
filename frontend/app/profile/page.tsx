"use client";

/**
 * Trait profile.
 *
 * Renders the six interpretable signals computed from the assessment answers
 * (lib/scoring.ts). Until this page had real input it showed a hardcoded
 * `sampleScores` object; that sample is still used, clearly labelled, when the
 * student has not taken the assessment yet, so the page never looks broken.
 */

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { AnimatedNumber } from "@/components/motion/animated-number";
import { traitLabels } from "@/lib/assessment";
import {
  FIELD_KEYS,
  TRAIT_KEYS,
  scoreFieldInterests,
  scoreTraits,
  type FieldScores,
  type TraitScores,
} from "@/lib/scoring";
import { useStoredAnswers } from "@/lib/use-assessment";
import { useEffect, useState } from "react";
import { fetchTimeline } from "@/lib/api";
import type { OpportunityField, TimelineEvent } from "@/lib/types";

const fieldLabels: Record<OpportunityField, string> = {
  cs: "Computer science",
  biology: "Biology",
  math: "Mathematics",
  physics: "Physics",
  engineering: "Engineering",
  interdisciplinary: "Interdisciplinary",
};

/** Preview distribution, shown until a real assessment exists. */
const sampleFieldScores: FieldScores = {
  cs: 34,
  engineering: 22,
  math: 16,
  biology: 12,
  physics: 9,
  interdisciplinary: 7,
};

/** Shown only when no assessment has been taken — labelled as a preview. */
const sampleScores: TraitScores = {
  builder: 82,
  analyst: 74,
  riskTolerance: 61,
  ambiguityComfort: 78,
  collaboration: 68,
  executionTempo: 85,
};

export default function ProfilePage() {
  const answers = useStoredAnswers();
  const isReal = answers !== null;
  const scores: TraitScores = isReal ? scoreTraits(answers) : sampleScores;
  const fieldScores: FieldScores = isReal
    ? scoreFieldInterests(answers)
    : sampleFieldScores;

  const ordered = [...TRAIT_KEYS].sort((a, b) => scores[b] - scores[a]);
  const top = ordered[0];
  const orderedFields = [...FIELD_KEYS].sort(
    (a, b) => fieldScores[b] - fieldScores[a],
  );

  // "Since last visit" — the evolving profile made visible. The previous
  // field distribution is snapshotted in localStorage; when it differs we
  // name the biggest movers, then store the current one.
  const [shifts, setShifts] = useState<string[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[] | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetchTimeline()
      .then((events) => {
        if (!cancelled) setTimeline(events);
      })
      .catch(() => {
        // Signed out — the localStorage shift note still works.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Prefer the server-side shift (computed between durable history
  // snapshots) over the localStorage one when a session exists.
  const serverShift = timeline?.find(
    (event) =>
      event.kind === "assessment" && event.detail !== "first profile snapshot",
  )?.detail;
  useEffect(() => {
    if (!isReal) return;
    const KEY = "northstar.profile.fieldSnapshot";
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        const previous = JSON.parse(raw) as Record<string, number>;
        const moved = FIELD_KEYS.map((field) => ({
          field,
          delta: fieldScores[field] - (previous[field] ?? 0),
        }))
          .filter(({ delta }) => delta !== 0)
          .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))
          .slice(0, 2)
          .map(
            ({ field, delta }) =>
              `${fieldLabels[field]} ${delta > 0 ? "+" : ""}${delta}`,
          );
        setShifts(moved);
      }
      localStorage.setItem(KEY, JSON.stringify(fieldScores));
    } catch {
      // Storage unavailable — the note just doesn't render.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isReal, JSON.stringify(fieldScores)]);

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Link
              href="/assessment"
              className="text-sm font-semibold text-aurora"
            >
              Back to assessment
            </Link>
            <h1 className="h-display mt-3 text-4xl text-foreground">
              Trait profile
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
              {isReal
                ? `Six trait signals and a field-interest map scored from your fourteen answers. Your strongest signal is ${traitLabels[top].toLowerCase()}.`
                : "This preview shows the six interpretable signals Northstar computes from assessment choices."}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <Button render={<Link href="/futures" />} className="h-11 px-5 font-semibold">
              Generate futures
            </Button>
            <ThemeToggle />
          </div>
        </header>

        {!isReal ? (
          <section className="mt-6 rounded-md border border-star bg-star/8 p-4">
            <p className="text-sm leading-6 text-foreground">
              These are sample numbers.{" "}
              <Link
                href="/assessment"
                className="font-semibold text-star underline"
              >
                Take the assessment
              </Link>{" "}
              to replace them with your own.
            </p>
          </section>
        ) : null}

        <section className="rounded-lg border bg-card mt-8 p-5">
          <div className="grid gap-5">
            {ordered.map((trait) => (
              <div key={trait}>
                <div className="mb-2 flex items-center justify-between gap-4">
                  <span className="text-sm font-semibold text-foreground">
                    {traitLabels[trait]}
                  </span>
                  <span className="font-mono text-sm text-star">
                    <AnimatedNumber
                      value={scores[trait]}
                      springOptions={{ bounce: 0, duration: 1200 }}
                    />
                    /100
                  </span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-panel-raised">
                  <div
                    className="h-full rounded-full bg-star transition-all"
                    style={{ width: `${scores[trait]}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border bg-card mt-8 p-5">
          <h2 className="text-sm font-semibold text-foreground">
            Field interest
          </h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            Where your answers pointed, as shares of a whole — the six numbers
            always sum to 100.
          </p>
          {serverShift || shifts.length > 0 ? (
            <p className="mt-2 font-mono text-xs text-star">
              {serverShift
                ? `Latest shift: ${serverShift}`
                : `Since your last visit: ${shifts.join(", ")}`}
            </p>
          ) : null}
          <div className="mt-5 grid gap-4">
            {orderedFields.map((field) => (
              <div key={field}>
                <div className="mb-2 flex items-center justify-between gap-4">
                  <span className="text-sm text-foreground">
                    {fieldLabels[field]}
                  </span>
                  <span className="font-mono text-sm text-star">
                    <AnimatedNumber
                      value={fieldScores[field]}
                      springOptions={{ bounce: 0, duration: 1200 }}
                    />
                    %
                  </span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-panel-raised">
                  <div
                    className="h-full rounded-full bg-star transition-all"
                    style={{ width: `${fieldScores[field]}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        {timeline && timeline.length > 0 ? (
          <section className="rounded-lg border bg-card mt-8 p-5">
            <h2 className="text-sm font-semibold text-foreground">
              Evidence timeline
            </h2>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Every recorded step — assessments, missions, outcomes,
              bookmarks — newest first. This record is the product.
            </p>
            <ul className="mt-4 grid gap-3">
              {timeline.slice(0, 12).map((event, index) => (
                <li
                  key={`${event.kind}-${event.at}-${index}`}
                  className="flex flex-wrap items-baseline gap-x-3 gap-y-1"
                >
                  <span className="font-mono text-[11px] uppercase tracking-wider text-aurora">
                    {event.at ? event.at.slice(0, 10) : ""} · {event.kind}
                  </span>
                  <span className="text-sm font-semibold text-foreground">
                    {event.title}
                  </span>
                  {event.detail ? (
                    <span className="text-xs text-muted-foreground">
                      {event.detail}
                    </span>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <p className="mt-4 text-xs leading-5 text-muted-foreground">
          Each trait score is the sum of the trait weights on the answers you
          picked, divided by the highest total that trait could reach across
          all fourteen questions. Field interest divides each field&apos;s
          points by the total points across every field. See
          frontend/lib/scoring.ts.
        </p>
      </div>
    </main>
  );
}
