"use client";

/**
 * Behavioural assessment.
 *
 * The choices used to render as static <div>s, so the landing page's primary
 * CTA led to a page nothing could be done with. They are now real radio-style
 * buttons; the selections are scored by lib/scoring.ts and read back by
 * /profile and /futures.
 */

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ScrollProgress } from "@/components/motion/scroll-progress";
import { WaypointPath } from "@/components/decor/waypoints";
import { useRouter } from "next/navigation";
import {
  LIKERT_VALUES,
  assessmentQuestions,
  likertLabels,
} from "@/lib/assessment";
import { isComplete, scoreFieldInterests, scoreTraits } from "@/lib/scoring";
import { syncAssessmentProfile } from "@/lib/api";
import { useStoredAnswers, writeAnswers } from "@/lib/use-assessment";
import { AppNav } from "@/components/AppNav";

/** Both question kinds use the same selected/unselected treatment. */
function optionClass(selected: boolean, extra: string): string {
  return selected
    ? `rounded-md border-2 border-star bg-star/10 transition ${extra}`
    : `rounded-md border-2 border-border bg-card transition hover:border-input ${extra}`;
}

export default function AssessmentPage() {
  const router = useRouter();

  // Reading from the store rather than local state means a half-finished run
  // survives a refresh, and /profile sees the answers the moment they change.
  const answers = useStoredAnswers() ?? {};

  function choose(questionId: string, choiceId: string) {
    writeAnswers({ ...answers, [questionId]: choiceId });
  }

  const answered = Object.keys(answers).length;
  const total = assessmentQuestions.length;
  const complete = isComplete(answers);

  /**
   * Best-effort server sync before navigating: signed-in students get
   * their trait + field scores onto the student row (which makes /match
   * proportional); signed-out students just proceed, the profile page
   * works from localStorage either way.
   */
  function finishAssessment() {
    if (complete) {
      syncAssessmentProfile(
        scoreTraits(answers),
        scoreFieldInterests(answers),
      ).catch(() => {});
    }
    router.push("/profile");
  }
  const left = total - answered;

  return (
    <main className="bleed-root min-h-screen px-6 py-8 sm:px-8">
      <ScrollProgress className="fixed inset-x-0 top-0 z-50 h-0.5 bg-star" />
      <div className="mx-auto max-w-5xl">
        <AppNav homeHref="/dashboard"
          right={
            <>
              <Button
                disabled={!complete}
                onClick={finishAssessment}
                className="h-11 px-5 font-semibold"
              >
                {complete ? "See your profile" : `${answered} of ${total} answered`}
              </Button>
            </>
          }
         />

        <header className="pb-6">
            <Link
              href="/"
              className="text-sm font-semibold text-aurora"
            >
              Northstar
            </Link>
            <h1 className="h-display mt-3 text-title text-foreground">
              Assessment
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
              Twenty prompts: nine reveal how you build, analyze,
              collaborate, and handle risk; eleven reveal which fields actually
              pull you in. Rate the statements, pick the scenario that fits —
              there are no wrong answers.
            </p>
        </header>

        {/* Each prompt is a waypoint on the course; the warm node is
            the first one still unanswered. */}
        <WaypointPath
          className="mt-6"
          ariaLabel={`Assessment progress: ${answered} of ${total} answered`}
          steps={assessmentQuestions.map((question, index) => {
            const firstOpen = assessmentQuestions.findIndex(
              (q) => !answers[q.id],
            );
            return {
              state: answers[question.id]
                ? "done"
                : index === firstOpen
                  ? "current"
                  : "upcoming",
            };
          })}
        />

        <section className="mt-8 grid gap-4">
          {assessmentQuestions.map((question, index) => (
            <article key={question.id} className="rounded-lg border bg-card p-5">
              <p className="font-mono text-xs tracking-[0.2em] text-star">
                {String(index + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}
              </p>
              <h2 className="h-display mt-2 text-section text-foreground">
                {question.prompt}
              </h2>
              {question.kind === "likert" ? (
                <div
                  role="radiogroup"
                  aria-label={question.prompt}
                  className="mt-4"
                >
                  <div className="grid grid-cols-5 gap-2">
                    {LIKERT_VALUES.map((value) => {
                      const selected = answers[question.id] === String(value);
                      return (
                        <button
                          key={value}
                          type="button"
                          role="radio"
                          aria-checked={selected}
                          aria-label={likertLabels[value]}
                          onClick={() => choose(question.id, String(value))}
                          className={optionClass(
                            selected,
                            "flex flex-col items-center gap-1.5 px-2 py-3",
                          )}
                        >
                          <span className="font-mono text-sm text-star">
                            {value}
                          </span>
                          {/* Hidden on narrow screens, where five labels
                              side by side shred into unreadable columns;
                              the end anchors below carry the scale there. */}
                          <span className="hidden text-xs leading-4 text-foreground sm:block">
                            {likertLabels[value]}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  <div
                    aria-hidden="true"
                    className="mt-2 flex justify-between text-xs text-muted-foreground sm:hidden"
                  >
                    <span>{likertLabels[1]}</span>
                    <span>{likertLabels[5]}</span>
                  </div>
                </div>
              ) : (
                <div
                  role="radiogroup"
                  aria-label={question.prompt}
                  className="mt-4 grid gap-3 md:grid-cols-3"
                >
                  {question.choices.map((choice) => {
                    const selected = answers[question.id] === choice.id;
                    return (
                      <button
                        key={choice.id}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        onClick={() => choose(question.id, choice.id)}
                        className={optionClass(selected, "p-4 text-left")}
                      >
                        <p className="text-sm leading-6 text-foreground">
                          {choice.label}
                        </p>
                      </button>
                    );
                  })}
                </div>
              )}
            </article>
          ))}
        </section>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono text-sm text-muted-foreground">
            {complete
              ? "All twenty answered — your trait profile is ready."
              : `${left} ${left === 1 ? "question" : "questions"} left.`}
          </p>
          <Button
            disabled={!complete}
            onClick={finishAssessment}
            className="h-11 px-5 font-semibold"
          >
            Continue to profile
          </Button>
        </div>
      </div>
    </main>
  );
}
