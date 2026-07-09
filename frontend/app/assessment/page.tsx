import Link from "next/link";
import { assessmentQuestions } from "@/lib/assessment";

export default function AssessmentPage() {
  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="flex flex-col gap-4 border-b border-[var(--border)] pb-6 sm:flex-row sm:items-center sm:justify-between">
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
              risk.
            </p>
          </div>
          <Link
            href="/profile"
            className="inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
          >
            Continue to profile
          </Link>
        </header>

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
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                {question.choices.map((choice) => (
                  <div
                    key={choice.id}
                    className="rounded-md border border-[var(--border)] bg-white/70 p-4"
                  >
                    <p className="text-sm leading-6 text-[var(--foreground)]">
                      {choice.label}
                    </p>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
