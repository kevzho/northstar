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
import { AnimatedNumber } from "@/components/motion/animated-number";
import { traitDescriptions, traitLabels } from "@/lib/assessment";
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
import { authedFetch, fetchTimeline } from "@/lib/api";
import { FieldPlanet } from "@/components/decor/field-planets";
import { ProfileDetailsCard } from "@/components/ProfileDetailsCard";
import { DeleteAccountCard } from "@/components/DeleteAccountCard";
import { SharingCard } from "@/components/SharingCard";
import type { OpportunityField, StudentProfile, TimelineEvent } from "@/lib/types";
import { useRequireAuth } from "@/lib/use-require-auth";
import { AppNav } from "@/components/AppNav";
import { FieldSky } from "@/components/decor/field-sky";

const fieldLabels: Record<OpportunityField, string> = {
  cs: "Computer science",
  biology: "Biology",
  math: "Mathematics",
  physics: "Physics",
  engineering: "Engineering",
  interdisciplinary: "Interdisciplinary",
  design: "Design & Media",
  business: "Business",
  humanities: "Humanities",
  health: "Health",
};

/** Preview distribution, shown until a real assessment exists. */
const sampleFieldScores: FieldScores = {
  cs: 28,
  engineering: 18,
  math: 12,
  design: 10,
  biology: 8,
  business: 8,
  physics: 6,
  humanities: 4,
  health: 3,
  interdisciplinary: 3,
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
  // Built from this student's own assessment, so it needs an account.
  // Signed out this used to render a heading and an empty shell while the
  // API answered 401 — gated and broken look identical from there.
  useRequireAuth();
  const [shifts, setShifts] = useState<string[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[] | null>(null);
  // The delete confirmation types this back, so it has to be the address on the
  // account rather than anything the client guessed.
  const [email, setEmail] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetchTimeline()
      .then((events) => {
        if (!cancelled) setTimeline(events);
      })
      .catch(() => {
        // Signed out — the localStorage shift note still works.
      });
    authedFetch("/me")
      .then((response) => response.json())
      .then((me: StudentProfile) => {
        if (!cancelled) setEmail(me.email ?? null);
      })
      .catch(() => {
        // Signed out; the delete card asks for "your email" instead.
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
    <main className="bleed-root min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <AppNav homeHref="/dashboard"
          right={
            <>
              <Button render={<Link href="/futures" />} className="h-11 px-5 font-semibold">
                Generate futures
              </Button>
            </>
          }
         />

        <header className="pb-6">
            <Link
              href="/assessment"
              className="text-sm font-semibold text-aurora"
            >
              Back to assessment
            </Link>
            <h1 className="h-display mt-3 text-title text-foreground">
              Trait profile
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
              {isReal
                ? `Six trait signals and a field-interest map scored from your twenty answers. Your strongest signal is ${traitLabels[top].toLowerCase()}.`
                : "This preview shows the six interpretable signals Northstar computes from assessment choices."}
            </p>
        </header>

        <ProfileDetailsCard />

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

        {/*
          BARS ARE SCALED TO THIS STUDENT'S OWN STRONGEST SIGNAL, NOT TO 100.

          They used to fill `width: score%`, and the result read as a flat row
          of half-empty bars — a real profile came back analyst 48, risk 48,
          builder 45, ambiguity 42, collaboration 40, tempo 31, and looked like
          six ways of saying "average".

          It was not. Measured across 400 simulated answer sets, the raw signal
          has real spread (64-94 points of range per trait), but 56% of all
          scores land between 30 and 55, because the denominator is the score
          you would get by picking the most trait-maximising answer on all
          twenty questions. Nobody does that — the questions trade traits
          against each other — so the ceiling is unreachable and "48/100" reads
          as below-average when it is near the top of the achievable range.

          Scaling to the student's own maximum makes the SHAPE visible, which is
          the thing the profile is actually for: 48 against 31 is a real
          difference, and it was invisible when both were drawn against 100.

          NOT a percentile. That would need a population and there are no
          students yet, so claiming one would be the kind of unearned number
          this project removes everywhere else.
        */}
        <section className="rounded-lg border bg-card mt-8 p-5">
          <p className="text-note leading-6 text-muted-foreground">
            Bars are drawn against your own strongest signal, so the shape is
            readable. These compare your six signals to each other, not to other students.
          </p>
          <div className="mt-5 grid gap-5">
            {ordered.map((trait, index) => {
              const peak = Math.max(...TRAIT_KEYS.map((t) => scores[t]), 1);
              return (
              <div key={trait}>
                <div className="mb-2 flex items-center justify-between gap-4">
                  <span className="text-sm font-semibold text-foreground">
                    {traitLabels[trait]}
                  </span>
                  <span className="font-mono text-note text-muted-foreground">
                    {index === 0 ? "strongest" : `#${index + 1}`}
                    <span className="ml-2 text-star">
                      <AnimatedNumber
                        value={scores[trait]}
                        springOptions={{ bounce: 0, duration: 1200 }}
                      />
                    </span>
                  </span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-panel-raised">
                  <div
                    className="h-full rounded-full bg-star transition-all"
                    style={{ width: `${Math.round((scores[trait] / peak) * 100)}%` }}
                  />
                </div>
                <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
                  {traitDescriptions[trait]}
                </p>
              </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-lg border bg-card mt-8 p-5">
          <h2 className="text-note font-semibold text-foreground">
            Field interest
          </h2>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            Ten worlds, one sky. Your answers as shares of a whole, always
            summing to 100.
          </p>
          {serverShift || shifts.length > 0 ? (
            <p className="mt-2 font-mono text-xs text-star">
              {serverShift
                ? `Latest shift: ${serverShift}`
                : `Since your last visit: ${shifts.join(", ")}`}
            </p>
          ) : null}
          {/* The sky first: it answers "what is the shape of my interests" at a
              glance, which a ranked list of ten bars makes you work for. The
              list stays underneath, because small shares are unreadable as
              circles and a picture is unreadable by a screen reader. */}
          <FieldSky scores={fieldScores} labels={fieldLabels} />

          <div className="mt-5 grid gap-4">
            {orderedFields.map((field) => (
              <div key={field}>
                <div className="mb-2 flex items-center justify-between gap-4">
                  <span className="flex items-center gap-2 text-sm text-foreground">
                    <FieldPlanet field={field} className="h-5 w-5 text-aurora" />
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
            <h2 className="text-note font-semibold text-foreground">
              Evidence timeline
            </h2>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              Every recorded step, newest first: assessments, missions, outcomes,
              bookmarks.
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

        <SharingCard />

        <DeleteAccountCard email={email} />

        <p className="mt-4 text-xs leading-5 text-muted-foreground">
          Each trait score is the sum of the trait weights on the answers you
          picked, divided by the highest total that trait could reach across
          all twenty questions.{" "}
          <span className="text-foreground">
            That ceiling is not reachable in practice
          </span>{" "}
          — it assumes you picked the most extreme answer for that one trait on
          every question, and the questions trade traits against each other. So
          a raw score in the forties is near the top of the usable range, not
          the middle, which is why the bars above are drawn against your own
          strongest signal instead. Field interest divides each field&apos;s
          points by the total points across every field. See
          frontend/lib/scoring.ts.
        </p>
      </div>
    </main>
  );
}
