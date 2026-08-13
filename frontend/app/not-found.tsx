"use client";

/**
 * Top-level not-found UI. Renders for any unmatched route or for a route that
 * calls notFound() (e.g. /opportunities/[id] when the opportunity doesn't
 * exist or fails to load). The page uses the same Northstar header chrome as
 * the rest of the app.
 */

import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-5">
          <Link href="/" className="h-display text-xl text-[var(--foreground)]">
            Northstar
          </Link>
        </div>

        <section className="card mt-16 p-8 text-center">
          <p className="eyebrow">404 — off the chart</p>
          <h1 className="h-display mt-3 text-4xl text-[var(--foreground)]">
            Page not found
          </h1>
          <p className="mt-4 max-w-2xl mx-auto text-base leading-7 text-[var(--muted)]">
            We could not find what you were looking for. The link may be
            outdated or the opportunity was removed.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Link href="/dashboard" className="btn-primary h-11 px-5">
              Back to dashboard
            </Link>
            <Link href="/opportunities" className="btn-secondary h-11 px-5">
              Browse opportunities
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
