"use client";

/**
 * Route advisor, full page.
 *
 * The advisor's real home is now the corner guide, docked beside whatever page
 * the student is reading -- see components/AdvisorConsole.tsx for why. This
 * route stays because links to it exist and a bookmark should not 404, and it
 * renders the same component so the two cannot answer differently.
 */

import Link from "next/link";
import { AdvisorConsole } from "@/components/AdvisorConsole";
import { AppNav } from "@/components/AppNav";
import { useRequireAuth } from "@/lib/use-require-auth";

export default function AdvisorPage() {
  // Every question goes to POST /advisor, which is auth-gated and metered per
  // student. Signed out, a student could type a whole question and get a 401.
  useRequireAuth();

  return (
    <main className="bleed-root min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <AppNav
          homeHref="/dashboard"
          right={
            <Link href="/dashboard" className="text-sm font-semibold text-aurora">
              Back to dashboard
            </Link>
          }
        />

        <header className="mt-10">
          <p className="eyebrow">Exploration, not prediction</p>
          <h1 className="h-display mt-3 text-title text-foreground">
            Route advisor
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
            Ask about unusual directions, hybrid fields, or college majors the
            rankings can&apos;t see. The same box sits in the guide in the
            bottom-right corner of every page, so you can ask without leaving
            what you were reading.
          </p>
        </header>

        <section className="mt-8">
          <AdvisorConsole />
        </section>
      </div>
    </main>
  );
}
