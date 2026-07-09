import Link from "next/link";

const previewSections = [
  {
    title: "Northstar Trait Profile",
    description:
      "Convert choices into six interpretable signals: builder, analyst, risk, ambiguity, collaboration, and tempo.",
  },
  {
    title: "Future Paths",
    description:
      "Compare the student profile against archetypes and surface a safe, ambitious, and unconventional path.",
  },
  {
    title: "30-Day Plan",
    description:
      "Turn the chosen path into specific projects, outreach, skill-building, and application actions.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-8 sm:px-8 lg:px-10">
        <nav className="flex items-center justify-between border-b border-[var(--border)] pb-5">
          <Link
            href="/"
            className="text-lg font-semibold tracking-tight text-[var(--northstar-dark)]"
          >
            Meridian
          </Link>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-semibold text-[var(--northstar-dark)]"
            >
              Sign in
            </Link>
            <Link
              href="/assessment"
              className="rounded-md bg-[var(--northstar)] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--northstar-dark)]"
            >
              Start assessment
            </Link>
          </div>
        </nav>

        <div className="grid flex-1 items-center gap-12 py-14 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--amber)]">
              YouthCodeX AI MVP
            </p>
            <h1 className="max-w-3xl text-5xl font-semibold leading-[1.02] tracking-tight text-[var(--northstar-dark)] sm:text-6xl lg:text-7xl">
              Meridian
            </h1>
            <p className="mt-5 max-w-2xl text-2xl leading-9 text-[var(--foreground)]">
              Every student deserves a meridian.
            </p>
            <p className="mt-6 max-w-2xl text-base leading-8 text-[var(--muted)] sm:text-lg">
              Meridian is a personalized opportunity map for high school
              students. It begins with Northstar, a behavioral assessment that
              translates how students think, work, and choose into plausible
              futures and concrete next actions.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/login"
                className="inline-flex h-12 items-center justify-center rounded-md bg-[var(--northstar)] px-6 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--northstar-dark)]"
              >
                Sign in to start
              </Link>
              <Link
                href="/profile"
                className="inline-flex h-12 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--panel)] px-6 text-sm font-semibold text-[var(--northstar-dark)] transition hover:border-[var(--northstar)]"
              >
                Preview profile
              </Link>
            </div>
          </div>

          <div className="grid gap-4">
            {previewSections.map((section, index) => (
              <article
                key={section.title}
                className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5 shadow-sm"
              >
                <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-md bg-[#e4f3f2] text-sm font-bold text-[var(--northstar-dark)]">
                  {index + 1}
                </div>
                <h2 className="text-xl font-semibold text-[var(--foreground)]">
                  {section.title}
                </h2>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                  {section.description}
                </p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
