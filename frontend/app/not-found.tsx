"use client";

/**
 * Top-level not-found UI. Renders for any unmatched route or for a route that
 * calls notFound() (e.g. /opportunities/[id] when the opportunity doesn't
 * exist or fails to load). The page uses the same Northstar header chrome as
 * the rest of the app.
 */

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AppNav } from "@/components/AppNav";

export default function NotFound() {
  return (
    <main className="bleed-root min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <AppNav />

        <section className="rounded-lg border bg-card mt-16 p-8 text-center">
          <svg
            viewBox="0 0 96 40"
            aria-hidden="true"
            className="mx-auto h-16 w-40 text-foreground"
          >
            <circle
              cx="30"
              cy="20"
              r="14"
              fill="none"
              stroke="currentColor"
              strokeWidth="0.8"
              opacity="0.3"
            />
            <circle cx="30" cy="20" r="3" fill="currentColor" opacity="0.85" />
            <path
              d="M44 16q8-5 16-6"
              fill="none"
              stroke="currentColor"
              strokeWidth="0.8"
              strokeDasharray="2 3"
              opacity="0.4"
            />
            <circle cx="64" cy="9" r="2" fill="currentColor" opacity="0.6" />
          </svg>
          <p className="eyebrow mt-4">404 — off the chart</p>
          <h1 className="h-display mt-3 text-title text-foreground">
            Page not found
          </h1>
          <p className="mt-4 max-w-2xl mx-auto text-base leading-7 text-muted-foreground">
            This route drifted off the charted map. The link may be outdated
            or the opportunity was removed.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
            <Button render={<Link href="/dashboard" />} className="h-11 px-5 font-semibold">
              Back to dashboard
            </Button>
            <Button variant="outline" render={<Link href="/opportunities" />} className="h-11 px-5 font-semibold">
              Browse opportunities
            </Button>
          </div>
        </section>
      </div>
    </main>
  );
}
