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
import { traitLabels } from "@/lib/assessment";
import { TRAIT_KEYS, scoreTraits, type TraitScores } from "@/lib/scoring";
import { useStoredAnswers } from "@/lib/use-assessment";

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

  const ordered = [...TRAIT_KEYS].sort((a, b) => scores[b] - scores[a]);
  const top = ordered[0];

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
                ? `Six interpretable signals scored from your eight answers. Your strongest signal is ${traitLabels[top].toLowerCase()}.`
                : "This preview shows the six interpretable signals Northstar computes from assessment choices."}
            </p>
          </div>
          <Button render={<Link href="/futures" />} className="h-11 shrink-0 px-5 font-semibold">
            Generate futures
          </Button>
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
                    {scores[trait]}/100
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

        <p className="mt-4 text-xs leading-5 text-muted-foreground">
          Each score is the sum of the trait weights on the answers you picked,
          divided by the highest total that trait could reach across all eight
          questions. See frontend/lib/scoring.ts.
        </p>
      </div>
    </main>
  );
}
