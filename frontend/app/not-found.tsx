"use client";

/**
 * Top-level not-found UI. Renders for any unmatched route or for a route that
 * calls notFound() (e.g. /opportunities/[id] when the opportunity doesn't
 * exist or fails to load). The page uses the same Meridian header chrome as
 * the rest of the app.
 */

import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-5">
          <Link
            href="/"
            className="text-lg font-semibold tracking-tight text-[var(--northstar-dark)]"
          >
            Meridian
          </Link>
        </div>

        <section className="mt-16 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-8 text-center shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--amber)]">
            404
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[var(--northstar-dark)]">
            Page not found
          </h1>
          <p className="mt-4 max-w-2xl mx-auto text-base leading-7 text-[var(--muted)]">
            We could not find what you were looking for. The link may be
            outdated or the opportunity was removed.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Link
              href="/dashboard"
              className="inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
            >
              Back to dashboard
            </Link>
            <Link
              href="/opportunities"
              className="inline-flex h-11 items-center justify-center rounded-md border border-[var(--border)] bg-white px-5 text-sm font-semibold text-[var(--northstar-dark)] transition hover:border-[var(--northstar)]"
            >
              Browse opportunities
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
