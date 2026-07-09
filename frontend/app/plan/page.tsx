import Link from "next/link";

const actions = [
  {
    timeframe: "This week",
    items: [
      "Build a tiny portfolio project connected to the chosen future path.",
      "Write a one-page reflection on what felt energizing and what felt draining.",
      "Find three examples of students or builders already doing similar work.",
    ],
  },
  {
    timeframe: "This month",
    items: [
      "Publish the project with a short demo note.",
      "Reach out to two mentors, teachers, or older students for feedback.",
      "Choose one skill gap and complete a focused 5-hour learning sprint.",
      "Apply to one program, competition, internship, or community opportunity.",
    ],
  },
];

export default function PlanPage() {
  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="flex flex-col gap-4 border-b border-[var(--border)] pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Link
              href="/futures"
              className="text-sm font-semibold text-[var(--northstar)]"
            >
              Back to futures
            </Link>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[var(--northstar-dark)]">
              30-Day Plan
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--muted)]">
              A concrete action list that turns a future path into visible
              progress within one month.
            </p>
          </div>
          <Link
            href="/"
            className="inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
          >
            Return home
          </Link>
        </header>

        <section className="mt-8 grid gap-4 lg:grid-cols-2">
          {actions.map((group) => (
            <article
              key={group.timeframe}
              className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5 shadow-sm"
            >
              <h2 className="text-xl font-semibold text-[var(--foreground)]">
                {group.timeframe}
              </h2>
              <ul className="mt-5 grid gap-3">
                {group.items.map((item) => (
                  <li
                    key={item}
                    className="flex gap-3 rounded-md border border-[var(--border)] bg-white/70 p-4 text-sm leading-6 text-[var(--foreground)]"
                  >
                    <span className="mt-1 h-4 w-4 shrink-0 rounded border border-[var(--northstar)]" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}
