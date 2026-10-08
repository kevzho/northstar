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
 * FIVE DESTINATIONS, NOT TWENTY-TWO. The routes group into five things a
 * student is actually doing — finding something to apply to, finding something
 * to learn, working out what to do next, understanding themselves, and finding
 * people. Everything else is a detail page reached from one of those. A nav
 * listing every route would be the same problem with more words in it.
 *
 * WHY "LEARN" IS NOT A DETAIL PAGE UNDER "OPPORTUNITIES". A programme has a
 * deadline you can miss and a gate you might not pass. A free textbook has
 * neither. Filing the shelf under applications is how it ended up reachable
 * only from a roadmap step, and how the product had nothing to say to a student
 * in a month when nothing is open — which is most months.
 *
 * SIGNED OUT IT SHOWS WHAT WORKS SIGNED OUT. Three of the five need an account;
 * two do not. Offering a visitor five links that bounce them to /login is worse
 * than offering the two they can actually use, and collapsing to nothing at all
 * (which this did until the shelf went public) is worse than both. See
 * lib/use-require-auth.ts.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { StarGlyph } from "@/components/decor/star-glyph";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/use-auth";

/**
 * `match` is the route prefix that should light this item up. `open` marks the
 * destinations that work with no account, which are the only ones a visitor is
 * shown.
 */
const SECTIONS = [
  { href: "/opportunities", label: "Programs", match: "/opportunities", open: true },
  { href: "/learn", label: "Learn", match: "/learn", open: true },
  { href: "/plan", label: "Plan", match: "/plan", open: false },
  { href: "/profile", label: "You", match: "/profile", open: false },
  { href: "/discover", label: "People", match: "/discover", open: false },
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
        {!loading ? (
          <nav aria-label="Sections" className="flex items-center gap-1">
            {SECTIONS.filter((section) => signedIn || section.open).map((section) => {
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
