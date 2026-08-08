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
        <header className="flex flex-col gap-4 border-b border-[var(--border)] pb-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Link
              href="/"
              className="text-sm font-semibold text-[var(--northstar)]"
            >
              Northstar
            </Link>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[var(--northstar-dark)]">
              Assessment
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--muted)]">
              Eight behavioral prompts that reveal how a student builds,
              analyzes, collaborates, moves through uncertainty, and handles
              risk. Pick the option that fits best — there are no wrong answers.
            </p>
          </div>
          <button
            type="button"
            disabled={!complete}
            onClick={() => router.push("/profile")}
            className="inline-flex h-11 shrink-0 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {complete ? "See your profile" : `${answered} of ${total} answered`}
          </button>
        </header>

        <div className="mt-6 h-2 overflow-hidden rounded-full bg-[#e6e1d8]">
          <div
            className="h-full rounded-full bg-[var(--northstar)] transition-all"
            style={{ width: `${(answered / total) * 100}%` }}
          />
        </div>

        <section className="mt-8 grid gap-4">
          {assessmentQuestions.map((question, index) => (
            <article
              key={question.id}
              className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5 shadow-sm"
            >
              <p className="text-sm font-semibold text-[var(--amber)]">
                Question {index + 1} of {assessmentQuestions.length}
              </p>
              <h2 className="mt-2 text-xl font-semibold text-[var(--foreground)]">
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
                          ? "rounded-md border-2 border-[var(--northstar)] bg-[#e4f3f2] p-4 text-left transition"
                          : "rounded-md border-2 border-[var(--border)] bg-white/70 p-4 text-left transition hover:border-[var(--northstar)]"
                      }
                    >
                      <p className="text-sm leading-6 text-[var(--foreground)]">
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
          <p className="text-sm text-[var(--muted)]">
            {complete
              ? "All eight answered — your trait profile is ready."
              : `${left} ${left === 1 ? "question" : "questions"} left.`}
          </p>
          <button
            type="button"
            disabled={!complete}
            onClick={() => router.push("/profile")}
            className="inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            Continue to profile
          </button>
        </div>
      </div>
    </main>
  );
}
