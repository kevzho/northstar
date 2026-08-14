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
import { Progress } from "@/components/ui/progress";
import { useRouter } from "next/navigation";
import { assessmentQuestions } from "@/lib/assessment";
import { isComplete } from "@/lib/scoring";
import { useStoredAnswers, writeAnswers } from "@/lib/use-assessment";

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
  const left = total - answered;

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Link
              href="/"
              className="text-sm font-semibold text-aurora"
            >
              Northstar
            </Link>
            <h1 className="h-display mt-3 text-4xl text-foreground">
              Assessment
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
              Eight behavioral prompts that reveal how a student builds,
              analyzes, collaborates, moves through uncertainty, and handles
              risk. Pick the option that fits best — there are no wrong answers.
            </p>
          </div>
          <Button
            disabled={!complete}
            onClick={() => router.push("/profile")}
            className="h-11 shrink-0 px-5 font-semibold"
          >
            {complete ? "See your profile" : `${answered} of ${total} answered`}
          </Button>
        </header>

        <Progress
          value={(answered / total) * 100}
          aria-label="Assessment progress"
          className="mt-6"
        />

        <section className="mt-8 grid gap-4">
          {assessmentQuestions.map((question, index) => (
            <article key={question.id} className="rounded-lg border bg-card p-5">
              <p className="font-mono text-xs tracking-[0.2em] text-star">
                {String(index + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}
              </p>
              <h2 className="mt-2 text-xl font-semibold text-foreground">
                {question.prompt}
              </h2>
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
                      className={
                        selected
                          ? "rounded-md border-2 border-star bg-star/10 p-4 text-left transition"
                          : "rounded-md border-2 border-border bg-card p-4 text-left transition hover:border-input"
                      }
                    >
                      <p className="text-sm leading-6 text-foreground">
                        {choice.label}
                      </p>
                    </button>
                  );
                })}
              </div>
            </article>
          ))}
        </section>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono text-sm text-muted-foreground">
            {complete
              ? "All eight answered — your trait profile is ready."
              : `${left} ${left === 1 ? "question" : "questions"} left.`}
          </p>
          <Button
            disabled={!complete}
            onClick={() => router.push("/profile")}
            className="h-11 px-5 font-semibold"
          >
            Continue to profile
          </Button>
        </div>
      </div>
    </main>
  );
}
