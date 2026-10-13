"use client";

/**
 * Two live readouts of the catalog, for the marketing page.
 *
 * Both exist to answer the same doubt a visitor has about any student project:
 * is this a real, maintained thing, or a screenshot? A claim cannot settle
 * that. A deadline three days out, and a dated row that arrived this morning,
 * can.
 *
 * WHY THESE READ SUPABASE DIRECTLY. The backend's GET /catalog requires a
 * session, and this page is for people who do not have one. public.opportunities
 * carries `for select using (true)` from the core schema, and anon INSERT and
 * UPDATE were revoked in 20260921120000_rls_lockdown.sql, so the publishable key
 * can read the shelf and cannot touch it. Verified against production before
 * this shipped.
 *
 * FAILURE IS SILENCE. Every path that could produce an empty or wrong band
 * renders nothing instead: no data, a failed request, a catalog with no open
 * deadlines. A landing page with an empty scrolling strip on it looks broken in
 * a way that costs more than the feature earns, and inventing filler would
 * undo the point of the section it sits in.
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import { daysUntil } from "@/lib/countdown";
import { supabase } from "@/lib/supabase";

type Row = {
  id: string;
  title: string;
  deadline: string | null;
  audience: string | null;
  created_at?: string | null;
};

/** Today at local midnight, as an ISO date — the boundary for "still open". */
function todayISO(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function shortDate(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}


/**
 * One timestamp per mount, not one per render.
 *
 * react-hooks/purity forbids a bare Date.now() in a render body, and it is
 * right to: two calls in one render can straddle midnight and produce a row
 * that is both "2d" and "1d" in the same paint. Captured once in state, the
 * whole component agrees with itself.
 */
function useRenderClock(): number {
  const [now] = useState(() => Date.now());
  return now;
}

/**
 * A scrolling strip of deadlines that have not passed.
 *
 * Ordered soonest-first and capped, so it is the most urgent slice of the
 * catalog rather than a sample of it. Each item links to the listing: a ticker
 * that cannot be acted on is an advert for the product it is part of.
 */
export function DeadlineTicker() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const now = useRenderClock();

  useEffect(() => {
    let live = true;
    const open = (audience: string, limit: number) =>
      supabase
        .from("opportunities")
        .select("id, title, deadline, audience")
        .is("retired_at", null)
        .not("deadline", "is", null)
        .gte("deadline", todayISO())
        .eq("audience", audience)
        .order("deadline", { ascending: true })
        .limit(limit);

    // High school first, then college fills the rest.
    //
    // Ordering the whole catalog by deadline gave fourteen college hackathons,
    // because the college shelf is scraped daily and a hackathon's window is
    // days wide, while the high-school shelf is annual programmes whose
    // deadlines cluster in winter. A strip of college hackathons on the page
    // that sells the high-school shelf is not false, it is just aimed at
    // somebody else. There are usually only a handful of open high-school
    // deadlines, so college is what keeps the strip from being three items
    // long.
    Promise.all([open("high_school", 8), open("college", 14)]).then(
      ([hs, college]) => {
        if (!live) return;
        const first = hs.error || !hs.data ? [] : (hs.data as Row[]);
        const rest = college.error || !college.data ? [] : (college.data as Row[]);
        setRows([...first, ...rest].slice(0, 14));
      },
    );
    return () => {
      live = false;
    };
  }, []);

  if (!rows || rows.length === 0) return null;

  const item = (row: Row) => {
    const left = row.deadline ? daysUntil(row.deadline, now) : null;
    return (
      <Link
        href={`/opportunities/${row.id}`}
        className="group flex shrink-0 items-baseline gap-2 px-5 py-2.5 font-mono text-xs tracking-wide text-muted-foreground hover:text-foreground focus-visible:text-foreground"
      >
        <span aria-hidden className="text-star opacity-70">
          ✦
        </span>
        <span className="max-w-[22rem] truncate group-hover:underline">
          {row.title}
        </span>
        <span className="text-foreground/80">
          {row.deadline ? shortDate(row.deadline) : ""}
        </span>
        {left !== null && left <= 7 ? (
          <span className="text-star">
            {left <= 0 ? "today" : `${left}d`}
          </span>
        ) : null}
      </Link>
    );
  };

  return (
    <div className="marquee-band border-y border-border">
      <div className="marquee-track">
        {/* The real copy is a list, and the label sits ON the list: a bare div
            with aria-label has no role, so the label is dropped by most screen
            readers and the strip announces as fourteen unexplained links. */}
        <ul className="flex" aria-label="Opportunities closing soonest">
          {rows.map((r) => (
            <li key={`a-${r.id}`} className="flex shrink-0">
              {item(r)}
            </li>
          ))}
        </ul>
        {/* The clone only exists so the loop has no seam. aria-hidden alone is
            not enough — its links stay keyboard-focusable, so tabbing walks
            into content hidden from assistive tech and the focus ring vanishes
            off-screen. `inert` removes it from focus and from the a11y tree. */}
        <ul className="flex" aria-hidden inert>
          {rows.map((r) => (
            <li key={`b-${r.id}`} className="flex shrink-0">
              {item(r)}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/**
 * The three most recent additions to the high-school shelf, dated.
 *
 * Scoped to high_school deliberately: the college shelf is almost entirely
 * scraped hackathons, so "newest overall" would always be three hackathons and
 * would say nothing about the shelf this page is selling. Dates are the whole
 * point — an undated "new!" is a marketing word, a dated row is a fact.
 */
export function RecentlyAdded() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const now = useRenderClock();

  useEffect(() => {
    let live = true;
    supabase
      .from("opportunities")
      .select("id, title, deadline, audience, created_at")
      .is("retired_at", null)
      .eq("audience", "high_school")
      // Curated or explicitly verified only.
      //
      // The newest two rows on the shelf the morning this shipped were scraper
      // finds with no deadline, one of them titled "Global Research Fellowship
      // Finance Research Scholarship" — which is what an unreviewed title looks
      // like. Putting that under a paragraph about checking listings against the
      // program's own website would contradict the paragraph, and a judge who
      // clicks the newest thing on the landing page and finds nothing has
      // learned something true about the catalog.
      //
      // So: rows a person curated, or a row carrying a verified_at stamp. A
      // scraped find appears here once someone has checked it, which is the
      // right incentive — the section rewards verification rather than volume.
      .or("added_by.in.(seed,human),verified_at.not.is.null")
      .order("created_at", { ascending: false })
      .limit(3)
      .then(({ data, error }) => {
        if (!live) return;
        setRows(error || !data ? [] : (data as Row[]));
      });
    return () => {
      live = false;
    };
  }, []);

  // Silence beats a stale label.
  //
  // The newest curated high-school rows were 39 days old the day this shipped,
  // because the curated shelf does not change weekly — the scraped college
  // shelf does. "Recently added" over August dates in late September is the
  // kind of small lie that makes a visitor discount everything else on the
  // page, and the section exists to do the opposite. So it renders only when
  // there is something genuinely recent, and otherwise renders nothing at all.
  //
  // Practically: this stays invisible until a curated row is added or a scraped
  // find is verified. That is the incentive we want — it rewards checking a
  // listing, not importing one.
  const MAX_AGE_DAYS = 30;
  const fresh = (rows ?? []).filter((row) => {
    if (!row.created_at) return false;
    const age = (now - new Date(row.created_at).getTime()) / 86_400_000;
    return age <= MAX_AGE_DAYS;
  });

  if (fresh.length === 0) return null;

  return (
    <div className="mt-12 border-t border-border pt-8">
      <p className="eyebrow">Recently added to the shelf</p>
      <ul className="mt-5 grid gap-5 sm:grid-cols-3">
        {fresh.map((row) => (
          <li key={row.id}>
            <p className="font-mono text-xs tracking-wide text-muted-foreground">
              {row.created_at ? shortDate(row.created_at.slice(0, 10)) : "—"}
            </p>
            <Link
              href={`/opportunities/${row.id}`}
              className="mt-1 block text-base leading-7 text-foreground hover:underline"
            >
              {row.title}
            </Link>
            {row.deadline ? (
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                closes {shortDate(row.deadline)}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
