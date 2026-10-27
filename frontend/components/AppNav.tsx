"use client";

/**
 * The one in-app nav row: wordmark, the four places there are, page actions.
 *
 * WHAT THIS REPLACES. A wordmark and a page-specific right slot, and nothing
 * else, so the app was hub-and-spoke with a weak hub. Measured 2026-10-08:
 * /dashboard linked to eight places, and every other page linked to two to
 * five, mostly sideways or back. From /profile a student could reach only
 * /assessment and /futures. From /map, only /dashboard and /onboarding. /plan
 * could not reach the shelf or the map at all. Twenty-two routes, no way
 * across them.
 *
 * FIVE DESTINATIONS, NOT TWENTY-TWO. The routes group into five things a
 * student is actually doing, finding something to apply to, finding something
 * to learn, working out what to do next, understanding themselves, and finding
 * people. Everything else is a detail page reached from one of those. A nav
 * listing every route would be the same problem with more words in it.
 *
 * WHY "LEARN" IS NOT A DETAIL PAGE UNDER "OPPORTUNITIES". A programme has a
 * deadline you can miss and a gate you might not pass. A free textbook has
 * neither. Filing the shelf under applications is how it ended up reachable
 * only from a roadmap step, and how the product had nothing to say to a student
 * in a month when nothing is open, which is most months.
 *
 * SIGNED OUT IT SHOWS WHAT WORKS SIGNED OUT. Three of the five need an account;
 * two do not. Offering a visitor five links that bounce them to /login is worse
 * than offering the two they can actually use, and collapsing to nothing at all
 * (which this did until the shelf went public) is worse than both. See
 * lib/use-require-auth.ts.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FieldPlanet } from "@/components/decor/field-planets";
import { StarGlyph } from "@/components/decor/star-glyph";
import { fieldColor } from "@/lib/field-colors";
import type { OpportunityField } from "@/lib/types";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/use-auth";

/**
 * `match` is the route prefix that should light this item up. `open` marks the
 * destinations that work with no account, which are the only ones a visitor is
 * shown.
 */
const SECTIONS = [
  // Dashboard first, because it is where a signed-in student lands and there
  // was no way back to it from anywhere except the wordmark.
  { href: "/dashboard", label: "Dashboard", match: "/dashboard", open: false, planet: "interdisciplinary" },
  { href: "/opportunities", label: "Programs", match: "/opportunities", open: true, planet: "cs" },
  { href: "/learn", label: "Learn", match: "/learn", open: true, planet: "math" },
  { href: "/plan", label: "Plan", match: "/plan", open: false, planet: "engineering" },
  // "Profile", not "You". A student looking for their profile scans a nav for
  // the word and does not find it, and /profile is where the trait scores, the
  // field sky, the evidence timeline and the public-handle control all live.
  { href: "/profile", label: "Profile", match: "/profile", open: false, planet: "design" },
  // One destination, not two. Discover and Team up were separate entries that
  // both answer "find someone to work with"; splitting them made the social
  // half look twice as big as it is and sent students to whichever they
  // happened to click.
  { href: "/discover", label: "People", match: "/discover", open: false, planet: "humanities" },
] as const;

/**
 * Routes that belong to a section without sharing its prefix.
 *
 * Every in-app route must resolve to one of the five, or the nav shows nothing
 * highlighted and the student has no idea where they are. Audited 2026-10-18:
 * /advisor, /mentors/join and /p/[handle] all rendered an unlit nav.
 */
const ALIASES: Record<string, string> = {
  "/futures": "/profile",
  "/assessment": "/profile",
  "/map": "/plan",
  // Asking the advisor what to do next is planning, not a sixth place to go.
  "/advisor": "/plan",
  "/friends": "/discover",
  "/teamup": "/discover",
  "/mentors": "/discover",
  "/mentors/join": "/discover",
  "/projects": "/opportunities",
};

/** Prefixes for the same reason, where the route carries a parameter. */
const ALIAS_PREFIXES: [string, string][] = [
  // Another student's public page is part of finding people.
  ["/p/", "/discover"],
];

export function AppNav({
  homeHref = "/",
  right,
}: {
  /** Where the wordmark links; in-app pages usually point at /dashboard. */
  homeHref?: string;
  /** Page-specific actions rendered left of the theme toggle. */
  right?: React.ReactNode;
}) {
  async function signOut() {
    const { supabase } = await import("@/lib/supabase");
    await supabase.auth.signOut();
    window.location.href = "/";
  }

  const pathname = usePathname() || "/";
  const { user, loading } = useAuth();
  const signedIn = Boolean(user);

  const active =
    ALIASES[pathname] ??
    ALIAS_PREFIXES.find(([prefix]) => pathname.startsWith(prefix))?.[1] ??
    SECTIONS.find((s) => pathname.startsWith(s.match))?.href ??
    null;

  return (
    /*
      FLUSH TO THE TOP, AND IT STAYS THERE.

      This was a static row sitting inside the page's own `py-8`, so 32px of
      dead space opened above it and the bar read as a strip floating in the
      content rather than as the top of the application. It also scrolled away
     , on /learn, which is 16,000px tall, you lost every navigation link
      three screens in.

      `-mt-8` cancels the page padding above it; `py-4` gives the bar its own.
      `.bleed-bg` paints the background and the hairline out to the window
      edges while the contents stay aligned with the centred column, and it
      provides the bottom border, so `border-b` is gone from here rather than
      drawn twice. The landing page has worked this way since the sprite sky
      shipped; every other page just never got it.
    */
    <div className="bleed-bg sticky top-0 z-40 -mt-8 flex flex-wrap items-center justify-between gap-y-3 py-4">
      <div className="flex items-center gap-6">
        <Link href={homeHref} className="flex items-center gap-2 text-foreground">
          <StarGlyph className="h-3.5 w-3.5 text-star" />
          <span className="h-display text-xl">Northstar</span>
        </Link>

        {/* Hidden while the session resolves rather than flashing the wrong
            state on every hard refresh, the same reason use-require-auth
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
                      ? "flex items-center gap-1.5 border-b-2 border-star px-2 py-1 text-sm font-semibold text-foreground"
                      : "flex items-center gap-1.5 border-b-2 border-transparent px-2 py-1 text-sm font-medium text-muted-foreground hover:text-foreground"
                  }
                >
                  <FieldPlanet
                    field={section.planet as OpportunityField}
                    className="h-3.5 w-3.5"
                    style={{
                      color: current ? fieldColor(section.planet) : undefined,
                    }}
                  />
                  {section.label}
                </Link>
              );
            })}
          </nav>
        ) : null}
      </div>

      <div className="flex items-center gap-3">
        {right}
        {/* Account controls belong next to each other and on every page.
            "Edit profile" was a card three screens down the dashboard and
            "Sign out" was in the dashboard's own right slot, so from any other
            page there was no way to do either without going back first. */}
        {!loading && signedIn ? (
          <>
            <Link
              href="/profile"
              className="text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              Edit profile
            </Link>
            <button
              type="button"
              onClick={signOut}
              className="text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              Sign out
            </button>
          </>
        ) : null}
        <ThemeToggle />
      </div>
    </div>
  );
}
