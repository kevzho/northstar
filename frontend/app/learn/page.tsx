"use client";

/**
 * The shelf, free material a student can start tonight.
 *
 * WHY THIS PAGE EXISTS. Northstar was an opportunity hub with a learning
 * catalog hidden inside it. public.learning_resources had 40-odd verified free
 * rows and exactly one way in: a roadmap step on /plan, which needs an account,
 * an assessment, a charted path, and that path's skill rung to be the thing you
 * happened to want. A student who wanted to learn something the plan had not
 * told them to learn could not get at it.
 *
 * And a catalog of programmes answers "what can I apply to", which for most
 * students is not the question most of the year. Four of the shelf's deadlines
 * are open at any given time; a Tuesday in February has none. The honest answer
 * to "what do I do now" is usually not an application, it is a free course, a
 * problem set, a textbook somebody put online. That half needs no account, no
 * transcript, no teacher and no money, which is why this page is public.
 *
 * EVERY ROW SHOWS ITS RECEIPT. "Free" is a claim, and a student with no money
 * who clicks through to a paywall has been lied to by the thing that was
 * supposed to help. So each row quotes the sentence on the page that proves it,
 * and the API drops rows whose evidence went missing rather than serving them on
 * trust (app/resources.py).
 */

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { Button } from "@/components/ui/button";
import { FieldPlanet } from "@/components/decor/field-planets";
import { LoadingSection } from "@/components/decor/orbit-loader";
import { fetchPublicShelf, type ShelfResource } from "@/lib/api";
import { fieldColor } from "@/lib/field-colors";
import type { OpportunityField } from "@/lib/types";

const FIELD_LABELS: Record<string, string> = {
  cs: "Computer science",
  biology: "Biology",
  math: "Mathematics",
  physics: "Physics",
  engineering: "Engineering",
  interdisciplinary: "Interdisciplinary",
  design: "Design & media",
  business: "Business",
  humanities: "Humanities",
  health: "Health",
};

/** Gentlest entry point first — the same order app/resources.py serves in. */
const KIND_LABELS: Record<string, string> = {
  interactive: "Interactive",
  documentation: "Reference",
  course: "Course",
  "problem-set": "Problem set",
  "video-series": "Video series",
  pdf: "PDF",
  textbook: "Textbook",
};

type Group = {
  skillKey: string;
  /** The subject, two or three words. */
  name: string;
  /** What that subject actually means, when the row says. */
  gloss: string;
  rows: ShelfResource[];
};

/**
 * skill_label is written as "statistical honesty, confounders, base rates, and
 * when a trend is noise": a name and a gloss in one string, because on /plan it
 * is read inside a sentence. As a heading the whole thing wraps to three lines,
 * so it is split, the name leads, the gloss explains underneath.
 *
 * Em dash, en dash or a spaced hyphen, because the seeded rows use an em dash
 * and the first AI-imported row came back with an en dash. Splitting on one
 * character left "Full-stack web development – building front-end and back-end
 * web applications" as an eighty-character heading.
 */
function splitLabel(label: string): { name: string; gloss: string } {
  const [raw, ...rest] = label.split(/\s+[—–-]\s+/);
  const name = (raw || label).trim();
  return {
    // Headings are sentence case whatever the row stored, so twelve seeded
    // lowercase labels and two model-written capitalised ones do not read as
    // two different catalogs.
    name: name.charAt(0).toUpperCase() + name.slice(1),
    gloss: rest.join(" — ").trim(),
  };
}

export default function LearnPage() {
  const [shelf, setShelf] = useState<ShelfResource[] | null>(null);
  const [field, setField] = useState<string>("");
  const [kind, setKind] = useState<string>("");

  useEffect(() => {
    let live = true;
    fetchPublicShelf().then((rows) => {
      if (live) setShelf(rows);
    });
    return () => {
      live = false;
    };
  }, []);

  const filtered = useMemo(
    () =>
      (shelf ?? []).filter(
        (row) =>
          (!field || row.field === field) && (!kind || row.kind === kind),
      ),
    [shelf, field, kind],
  );

  // Grouped by what it teaches, not by who hosts it. A student looking for
  // statistics does not care whether it came from MIT or OpenIntro.
  const groups = useMemo(() => {
    const out = new Map<string, Group>();
    for (const row of filtered) {
      const existing = out.get(row.skill_key);
      if (existing) existing.rows.push(row);
      else
        out.set(row.skill_key, {
          skillKey: row.skill_key,
          ...splitLabel(row.skill_label || row.skill_key),
          rows: [row],
        });
    }
    // Case-insensitive, because the seeded labels are lowercase ("sampling
    // discipline") and the model-written ones are not ("Python programming
    // basics"), a raw sort put the two newest rows above all twelve others
    // for no reason a reader could see.
    return [...out.values()].sort((a, b) =>
      a.name.localeCompare(b.name, undefined, { sensitivity: "base" }),
    );
  }, [filtered]);

  const fieldsPresent = useMemo(() => {
    const seen = new Set<string>();
    for (const row of shelf ?? []) if (row.field) seen.add(row.field);
    return [...seen].sort((a, b) =>
      (FIELD_LABELS[a] ?? a).localeCompare(FIELD_LABELS[b] ?? b),
    );
  }, [shelf]);

  const kindsPresent = useMemo(() => {
    const seen = new Set<string>();
    for (const row of shelf ?? []) seen.add(row.kind);
    return [...seen].sort(
      (a, b) =>
        Object.keys(KIND_LABELS).indexOf(a) - Object.keys(KIND_LABELS).indexOf(b),
    );
  }, [shelf]);

  return (
    <main className="bleed-root min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <AppNav
          homeHref="/"
          right={
            <Link href="/opportunities" className="text-sm font-semibold text-aurora">
              Programmes with deadlines
            </Link>
          }
        />

        <header className="mt-10">
          <p className="eyebrow">The shelf</p>
          <h1 className="h-display mt-3 text-title text-foreground">
            Things you can start tonight
          </h1>
          <p className="mt-4 max-w-2xl text-lede text-muted-foreground">
            Free material, and no account needed here or on the other end. Every row quotes the sentence on its own page that proves it is
            free, because a student with no money who clicks through to a
            paywall has been failed by the thing that was supposed to help.
          </p>
          {shelf && shelf.length > 0 ? (
            <p className="mt-3 font-mono text-xs uppercase tracking-[0.16em] text-aurora">
              {shelf.length} resources · {new Set(shelf.map((r) => r.skill_key)).size}{" "}
              subjects · $0
            </p>
          ) : null}
        </header>

        {/* Why this page and /opportunities are different pages. A programme has
            a deadline you can miss and a gate you might not pass; a textbook
            has neither, and conflating them was how the catalog ended up with
            nothing to say to a student in February. */}
        <section className="mt-8 border border-border bg-panel-raised p-5">
          <p className="text-sm leading-7 text-muted-foreground">
            <span className="text-foreground">
              Applications are the smaller half of this.
            </span>{" "}
            Programmes open and close, and most of the year nothing you are
            eligible for is open. The work that gets you into one of them is
            always available, costs nothing, and is on this page.{" "}
            <Link href="/plan" className="font-semibold text-aurora">
              Your plan
            </Link>{" "}
            picks from this shelf and puts it in an order.
          </p>
        </section>

        {shelf === null ? (
          <LoadingSection label="Opening the shelf..." />
        ) : shelf.length === 0 ? (
          <section className="mt-10 rounded-lg border bg-card p-8 text-center">
            <h2 className="h-display text-section text-foreground">
              The shelf is not loading
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              The server did not answer. Reload, and if it keeps happening the
              catalog of programmes is still up.
            </p>
            <Button render={<Link href="/opportunities" />} className="mt-6 h-11 px-5">
              Browse programmes instead
            </Button>
          </section>
        ) : (
          <>
            <div className="mt-8 flex flex-col gap-3 border-b border-border pb-5">
              <Filter
                legend="Subject"
                options={[
                  { value: "", label: "All" },
                  ...fieldsPresent.map((value) => ({
                    value,
                    label: FIELD_LABELS[value] ?? value,
                  })),
                ]}
                value={field}
                onChange={setField}
                glyph
              />
              <Filter
                legend="Format"
                options={[
                  { value: "", label: "All" },
                  ...kindsPresent.map((value) => ({
                    value,
                    label: KIND_LABELS[value] ?? value,
                  })),
                ]}
                value={kind}
                onChange={setKind}
              />
            </div>

            {groups.length === 0 ? (
              <p className="mt-8 text-sm leading-6 text-muted-foreground">
                Nothing on the shelf matches that yet. The shelf grows by
                verification, not by volume. An unverified row would be worth
                less than an empty filter.
              </p>
            ) : (
              <div className="mt-8 grid gap-8">
                {groups.map((group) => (
                  <section
                    key={group.skillKey}
                    id={`shelf-${group.skillKey}`}
                    className="scroll-mt-6"
                  >
                    <h2 className="h-display flex items-center gap-2 text-section text-foreground">
                      <FieldPlanet
                        field={
                          (group.rows[0].field as OpportunityField) ??
                          "interdisciplinary"
                        }
                        className="h-5 w-5"
                        style={
                          group.rows[0].field
                            ? { color: fieldColor(group.rows[0].field) }
                            : undefined
                        }
                      />
                      {group.name}
                    </h2>
                    {group.gloss ? (
                      <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
                        {group.gloss}
                      </p>
                    ) : null}
                    <ul className="mt-3 grid gap-3">
                      {group.rows.map((row) => (
                        <li
                          key={row.id}
                          className="rounded-md border border-border bg-card p-4"
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded border border-input bg-panel px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-aurora">
                              {KIND_LABELS[row.kind] ?? row.kind}
                            </span>
                            <span className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-polaris">
                              free
                            </span>
                            <span className="font-mono text-xs text-muted-foreground">
                              {row.effort}
                            </span>
                          </div>
                          <a
                            href={row.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-2 block text-base font-semibold leading-6 text-foreground underline decoration-border underline-offset-4 hover:decoration-primary"
                          >
                            {row.title}
                            <span className="ml-2 font-mono text-xs font-normal text-muted-foreground">
                              {row.host}
                            </span>
                          </a>
                          {/* TWO LINES BY DEFAULT, THE REST ON REQUEST.
                              Measured across the shelf: why_this_one runs to
                              699 characters and the free-evidence quote to
                              599, with 42 of 109 rows over 300. Printed in
                              full, every card was a paragraph and the page was
                              a wall you scroll rather than a shelf you scan.

                              Clamped, NOT truncated: nothing is cut from the
                              data and the quote is never shortened, because a
                              receipt that has been trimmed is not a receipt.
                              A native <details> holds the rest, so it opens
                              with the keyboard and needs no state. */}
                          {row.why_this_one ? (
                            <p className="mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground">
                              {row.why_this_one}
                            </p>
                          ) : null}
                          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs leading-5 text-muted-foreground">
                            <span>
                              <span className="text-foreground">Needs first:</span>{" "}
                              {row.prerequisite || "nothing"}
                            </span>
                          </div>
                          <details className="group mt-2">
                            <summary className="cursor-pointer list-none text-xs text-aurora marker:hidden">
                              <span className="group-open:hidden">
                                Why this one, and the line that proves it is free
                              </span>
                              <span className="hidden group-open:inline">Close</span>
                            </summary>
                            {row.why_this_one ? (
                              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                                {row.why_this_one}
                              </p>
                            ) : null}
                            {/* The receipt. Quoted, not paraphrased, the
                                words on their page, so a student can check
                                us. Never clamped. */}
                            {row.free_evidence ? (
                              <p className="mt-2 border-l border-border pl-3 text-xs leading-5 text-muted-foreground italic">
                                &ldquo;{row.free_evidence}&rdquo;
                              </p>
                            ) : null}
                          </details>
                        </li>
                      ))}
                    </ul>
                  </section>
                ))}
              </div>
            )}

            <section className="mt-12 border-t border-border pt-6">
              <h2 className="h-display text-section text-foreground">
                Something missing?
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-muted-foreground">
                This shelf is short on purpose. Every row was opened, read, and
                quoted before it went up, and that is slower than scraping a
                thousand links. But a list of free resources where three are
                paywalled is worse for a student with no money than a list of
                forty where none are.{" "}
                <Link href="/contact" className="font-semibold text-aurora">
                  Send us one that helped you
                </Link>
                .
              </p>
            </section>
          </>
        )}
      </div>
    </main>
  );
}

function Filter({
  legend,
  options,
  value,
  onChange,
  glyph = false,
}: {
  legend: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (next: string) => void;
  glyph?: boolean;
}) {
  return (
    <fieldset className="flex flex-wrap items-center gap-2">
      <legend className="sr-only">{legend}</legend>
      <span className="font-mono text-[0.65rem] uppercase tracking-[0.16em] text-muted-foreground">
        {legend}
      </span>
      {options.map((option) => {
        const on = value === option.value;
        return (
          <button
            key={option.value || "all"}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(option.value)}
            className={`flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs transition-colors ${
              on
                ? "border-star bg-star/10 text-foreground"
                : "border-border bg-panel text-muted-foreground hover:text-foreground"
            }`}
          >
            {glyph && option.value ? (
              <FieldPlanet
                field={option.value as OpportunityField}
                className="h-3 w-3"
                style={{ color: fieldColor(option.value) }}
              />
            ) : null}
            {option.label}
          </button>
        );
      })}
    </fieldset>
  );
}
