"use client";

/**
 * Polaris — the corner guide.
 *
 * A fixed assistant in the bottom-right of every page. Deliberately
 * deterministic: it explains the page you are on (what it is, what to do
 * next, where it leads) from a hand-written route map, so it works
 * signed-out, offline from the backend, and without any LLM key. The
 * conversational route advisor stays its own page; the guide links there
 * for open-ended questions instead of pretending to be one.
 */

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { StarGlyph } from "@/components/decor/star-glyph";

type GuideEntry = {
  title: string;
  tips: string[];
  links?: { href: string; label: string }[];
};

const DEFAULT_ENTRY: GuideEntry = {
  title: "Finding your bearings",
  tips: [
    "Northstar maps who you are to real STEM opportunities.",
    "The dashboard is home base — everything routes from there.",
  ],
  links: [{ href: "/dashboard", label: "Open the dashboard" }],
};

/** Longest-prefix wins, so /opportunities/123 matches /opportunities. */
const GUIDE: [string, GuideEntry][] = [
  [
    "/dashboard",
    {
      title: "Home base",
      tips: [
        "Your charted path, next waypoint, and today's moves live here.",
        "Stuck on direction? The route advisor answers open questions.",
      ],
      links: [
        { href: "/opportunities", label: "Browse opportunities" },
        { href: "/advisor", label: "Ask the route advisor" },
      ],
    },
  ],
  [
    "/onboarding",
    {
      title: "Charting you",
      tips: [
        "Answer honestly — there are no wrong answers, only wrong fits.",
        "Your profile stays private unless you later opt in to sharing.",
      ],
    },
  ],
  [
    "/assessment",
    {
      title: "The assessment",
      tips: [
        "Twenty prompts, about five minutes, no right answers.",
        "Scores become your trait shape — the engine ranks against it.",
      ],
    },
  ],
  [
    "/opportunities",
    {
      title: "The opportunity bank",
      tips: [
        "“For you” is ranked against your profile; “All” is the full catalog.",
        "Log outcomes when you hear back — accepted or not, it sharpens your map.",
      ],
      links: [{ href: "/map", label: "See your pathway map" }],
    },
  ],
  [
    "/map",
    {
      title: "Your pathway map",
      tips: [
        "Each field is a star; the programs matched to you orbit it. Inner orbits close soonest.",
        "The warm mark is always you — your current waypoint.",
      ],
    },
  ],
  [
    "/teamup",
    {
      title: "Team up",
      tips: [
        "Collaborator matching, not chat: picks stay invisible unless mutual.",
        "“Full details” on any card shows their pitch and path.",
        "Report and block work on every card, and you can leave the pool anytime.",
      ],
    },
  ],
  [
    "/discover",
    {
      title: "Discover peers",
      tips: [
        "Only students who opted in appear here — same for your own visibility.",
        "Friend requests unlock the side-by-side comparison.",
      ],
      links: [{ href: "/friends", label: "Manage friends" }],
    },
  ],
  [
    "/friends",
    {
      title: "Friends",
      tips: [
        "Accepted friends can compare trait shapes and mission counts.",
        "Negative outcomes are never shown — only counts, never which programs.",
      ],
    },
  ],
  [
    "/mentors",
    {
      title: "Mentors",
      tips: [
        "Ranked by overlap with your fields. The directory is empty until mentors opt in.",
        "A short, specific first message beats a long generic one.",
      ],
    },
  ],
  [
    "/plan",
    {
      title: "Your plan",
      tips: [
        "A season-by-season sequence built from your verified matches.",
        "Deadlines drive the order — earliest commitments surface first.",
      ],
    },
  ],
  [
    "/projects",
    {
      title: "Project ideas",
      tips: [
        "Real open-source projects matched to your leading fields.",
        "Shipping one small contribution outweighs ten bookmarks.",
      ],
    },
  ],
  [
    "/futures",
    {
      title: "Future paths",
      tips: [
        "Long-range directions ranked against your six trait scores.",
        "Exploration, not prophecy — treat these as headings, not verdicts.",
      ],
    },
  ],
  [
    "/profile",
    {
      title: "Your record",
      tips: [
        "Everything about you is editable here on one page.",
        "Social links show on your public record only, and only if you opt in.",
      ],
    },
  ],
  [
    "/advisor",
    {
      title: "Route advisor",
      tips: [
        "Ask about hybrid fields and unusual routes — answers cite your verified matches.",
        "This page never scores; the deterministic engine keeps that job.",
      ],
    },
  ],
  [
    "/p/",
    {
      title: "A public record",
      tips: [
        "Opt-in highlights only: shape, missions, and positive outcomes.",
        "Rejections are never public, for anyone.",
      ],
    },
  ],
  [
    "/login",
    {
      title: "Signing in",
      tips: [
        "One account carries your assessment, matches, and record.",
        "New here? The quiz starts right after you sign up.",
      ],
    },
  ],
  [
    "/",
    {
      title: "Welcome aboard",
      tips: [
        "Northstar turns a short assessment into a personal map of real STEM opportunities.",
        "Start with the quiz — the whole first pass takes about five minutes.",
      ],
      links: [{ href: "/login", label: "Start your chart" }],
    },
  ],
];

function entryFor(pathname: string): GuideEntry {
  if (pathname === "/") return GUIDE[GUIDE.length - 1][1];
  for (const [prefix, entry] of GUIDE) {
    if (prefix !== "/" && pathname.startsWith(prefix)) return entry;
  }
  return DEFAULT_ENTRY;
}

export function Guide() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Close when navigating so the panel always describes the current page —
  // state adjusted during render, per the React "you might not need an
  // effect" pattern.
  const [lastPath, setLastPath] = useState(pathname);
  if (pathname !== lastPath) {
    setLastPath(pathname);
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    window.addEventListener("pointerdown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open]);

  if (pathname?.startsWith("/auth")) return null;

  const entry = entryFor(pathname ?? "/");

  return (
    <div
      ref={rootRef}
      className="fixed bottom-4 right-4 z-40 flex flex-col items-end gap-3 sm:bottom-6 sm:right-6"
    >
      {open ? (
        <section
          role="dialog"
          aria-label="Polaris guide"
          className="w-80 max-w-[calc(100vw-2rem)] rounded-lg border bg-card p-5 shadow-xl"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="eyebrow">Polaris · guide</p>
              <h2 className="h-display mt-1 text-lg text-foreground">
                {entry.title}
              </h2>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close the guide"
              className="font-mono text-xs text-muted-foreground transition hover:text-foreground"
            >
              ✕
            </button>
          </div>
          <ul className="mt-3 grid gap-2 text-sm leading-6 text-muted-foreground">
            {entry.tips.map((tip) => (
              <li key={tip} className="flex gap-2">
                <StarGlyph className="mt-1.5 h-2.5 w-2.5 shrink-0 text-star" />
                <span>{tip}</span>
              </li>
            ))}
          </ul>
          {entry.links?.length ? (
            <div className="mt-4 flex flex-wrap gap-2 border-t border-border pt-3">
              {entry.links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="border border-border px-3 py-1.5 text-xs font-semibold text-foreground transition hover:border-foreground"
                >
                  {link.label} →
                </Link>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}
      {/*
        The button is a star glyph and nothing else, which means its job is
        guessable at best. A label on hover and on keyboard focus says what it
        does before someone has to click to find out.

        group-hover AND group-focus-within, not hover alone: a keyboard user
        tabbing to this button gets the same answer a mouse user gets, and the
        aria-label already carries it for a screen reader. Hidden from
        assistive tech so it is not announced twice.
      */}
      <span className="group relative flex">
        <span
          aria-hidden="true"
          className="pointer-events-none absolute right-full top-1/2 mr-3 -translate-y-1/2 whitespace-nowrap border border-border bg-card px-3 py-1.5 text-note text-foreground opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
        >
          {open ? "Close" : "Press me for info"}
        </span>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-label={open ? "Close the guide" : "Open the guide"}
        className="flex h-12 w-12 items-center justify-center rounded-full border border-border bg-card text-star shadow-lg transition hover:border-foreground"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true" className="h-6 w-6">
          <circle
            cx="12"
            cy="12"
            r="8.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            opacity="0.4"
          />
          <path
            fill="currentColor"
            d="M12 6.5q0.9 4.6 5.5 5.5-4.6 0.9-5.5 5.5-0.9-4.6-5.5-5.5 4.6-0.9 5.5-5.5Z"
          />
          <circle cx="19" cy="7" r="1.1" fill="currentColor" opacity="0.7" />
        </svg>
      </button>
      </span>
    </div>
  );
}
