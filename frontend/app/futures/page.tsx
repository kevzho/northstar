import Link from "next/link";
import { archetypes } from "@/lib/archetypes";

const pathTypes = ["Safe fit", "Ambitious fit", "Unconventional fit"];

export default function FuturesPage() {
  const featuredPaths = archetypes.slice(0, 3);

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="flex flex-col gap-4 border-b border-[var(--border)] pb-6 sm:flex-row sm:items-center sm:justify-between">
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
            className="inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
          >
            Choose a path
          </Link>
        </header>

        <section className="mt-8 grid gap-4 lg:grid-cols-3">
          {featuredPaths.map((path, index) => (
            <article
              key={path.id}
              className="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5 shadow-sm"
            >
              <p className="text-sm font-semibold text-[var(--amber)]">
                {pathTypes[index]}
              </p>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-[var(--foreground)]">
                {path.label}
              </h2>
              <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
                {path.summary}
              </p>
            </article>
          ))}
        </section>

        <section className="mt-8 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">
            Archetype library
          </h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {archetypes.map((path) => (
              <div
                key={path.id}
                className="rounded-md border border-[var(--border)] bg-white/70 p-4"
              >
                <p className="font-semibold text-[var(--northstar-dark)]">
                  {path.label}
                </p>
                <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                  {path.summary}
                </p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
