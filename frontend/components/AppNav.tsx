"use client";

/**
 * The one in-app nav row: wordmark, the four places there are, page actions.
 *
 * WHAT THIS REPLACES. A wordmark and a page-specific right slot, and nothing
 * else — so the app was hub-and-spoke with a weak hub. Measured 2026-10-08:
 * /dashboard linked to eight places, and every other page linked to two to
 * five, mostly sideways or back. From /profile a student could reach only
 * /assessment and /futures. From /map, only /dashboard and /onboarding. /plan
 * could not reach the shelf or the map at all. Twenty-two routes, no way
 * across them.
 *
 * FOUR DESTINATIONS, NOT TWENTY-TWO. The routes group into four things a
 * student is actually doing — finding something to apply to, working out what
 * to do next, understanding themselves, and finding people. Everything else is
 * a detail page reached from one of those. A nav listing every route would be
 * the same problem with more words in it.
 *
 * SIGNED OUT IT COLLAPSES. Three of the four need an account, and offering a
 * visitor four links that bounce them to /login is worse than offering the one
 * thing they can actually use. See lib/use-require-auth.ts.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { StarGlyph } from "@/components/decor/star-glyph";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/use-auth";

/** `match` is the route prefix that should light this item up. */
const SECTIONS = [
  { href: "/opportunities", label: "Opportunities", match: "/opportunities" },
  { href: "/plan", label: "Plan", match: "/plan" },
  { href: "/profile", label: "You", match: "/profile" },
  { href: "/discover", label: "People", match: "/discover" },
] as const;

/** Routes that belong to a section without sharing its prefix. */
const ALIASES: Record<string, string> = {
  "/futures": "/profile",
  "/assessment": "/profile",
  "/map": "/plan",
  "/friends": "/discover",
  "/teamup": "/discover",
  "/mentors": "/discover",
  "/projects": "/opportunities",
};

export function AppNav({
  homeHref = "/",
  right,
}: {
  /** Where the wordmark links; in-app pages usually point at /dashboard. */
  homeHref?: string;
  /** Page-specific actions rendered left of the theme toggle. */
  right?: React.ReactNode;
}) {
  const pathname = usePathname() || "/";
  const { user, loading } = useAuth();
  const signedIn = Boolean(user);

  const active =
    ALIASES[pathname] ??
    SECTIONS.find((s) => pathname.startsWith(s.match))?.href ??
    null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-y-3 border-b border-border pb-5">
      <div className="flex items-center gap-6">
        <Link href={homeHref} className="flex items-center gap-2 text-foreground">
          <StarGlyph className="h-3.5 w-3.5 text-star" />
          <span className="h-display text-xl">Northstar</span>
        </Link>

        {/* Hidden while the session resolves rather than flashing the wrong
            state on every hard refresh — the same reason use-require-auth
            waits before redirecting. */}
        {!loading && signedIn ? (
          <nav aria-label="Sections" className="flex items-center gap-1">
            {SECTIONS.map((section) => {
              const current = active === section.href;
              return (
                <Link
                  key={section.href}
                  href={section.href}
                  aria-current={current ? "page" : undefined}
                  className={
                    current
                      ? "border-b-2 border-star px-2 py-1 text-sm font-semibold text-foreground"
                      : "border-b-2 border-transparent px-2 py-1 text-sm font-medium text-muted-foreground hover:text-foreground"
                  }
                >
                  {section.label}
                </Link>
              );
            })}
          </nav>
        ) : null}
      </div>

      <div className="flex items-center gap-3">
        {right}
        <ThemeToggle />
      </div>
    </div>
  );
}
