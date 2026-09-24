"use client";

/**
 * 30-day plan — generated, not hardcoded.
 *
 * The plan is assembled by lib/plan.ts from the chosen future path, the trait
 * profile, and (when signed in) the student's real ranked matches with their
 * deadlines. Signed out, the plan still generates from path + traits and says
 * plainly what signing in would add.
 */

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, useScroll, useTransform } from "motion/react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { Planet, Ship } from "@/components/decor/voyage";
import { fetchMatches, fetchResources } from "@/lib/api";
import type { LearningResource } from "@/lib/api";
import { MissionBoard } from "@/components/MissionBoard";
import { findArchetype, generatePlan, skillKeyFor } from "@/lib/plan";
import { pathLabel, rankArchetypes, scoreTraits } from "@/lib/scoring";
import type { MatchResult } from "@/lib/types";
import { useStoredAnswers } from "@/lib/use-assessment";
import { useChosenPath } from "@/lib/use-chosen-path";

const LEG_PLANETS = ["moon", "ringed", "giant"] as const;

export default function PlanPage() {
  const voyageRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: voyageRef,
    offset: ["start 0.7", "end 0.7"],
  });
  const shipTop = useTransform(scrollYProgress, [0, 1], ["1%", "97%"]);
  const answers = useStoredAnswers();
  const chosen = useChosenPath();
  const [matches, setMatches] = useState<MatchResult[] | null>(null);
  const [matchesSettled, setMatchesSettled] = useState(false);
  // Free material for this path's skill rung. Additive: the plan renders
  // without it, because the step itself is still a real instruction.
  const [resources, setResources] = useState<LearningResource[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchMatches();
        if (!cancelled) setMatches(data);
      } catch {
        // Signed out or backend unreachable — the plan generates without
        // application targets and the page says what signing in adds.
        if (!cancelled) setMatches(null);
      } finally {
        if (!cancelled) setMatchesSettled(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const traits = answers ? scoreTraits(answers) : null;
  const archetype = chosen ? findArchetype(chosen.archetypeId) : null;
  const skillKey = chosen ? skillKeyFor(chosen.archetypeId) : "";

  useEffect(() => {
    if (!skillKey) return;
    let live = true;
    fetchResources(skillKey).then((rows) => {
      if (live) setResources(rows);
    });
    return () => {
      live = false;
    };
  }, [skillKey]);
  const fit =
    traits && archetype
      ? rankArchetypes(traits).find((r) => r.archetype.id === archetype.id)
          ?.fit ?? null
      : null;

  const plan =
    traits && archetype && chosen
      ? generatePlan(archetype, chosen.kind, traits, matches, new Date())
      : null;

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Link href="/futures" className="text-sm font-semibold text-aurora">
              Back to futures
            </Link>
            <h1 className="h-display mt-3 text-4xl text-foreground">
              30-day plan
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
              {archetype && chosen
                ? `Built from your ${pathLabel(chosen.kind).toLowerCase()} — ${
                    archetype.label
                  }${fit !== null ? ` (${fit}% fit)` : ""} — your trait profile, and your ranked matches.`
                : "A concrete action list that turns a future path into visible progress within one month."}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            {archetype ? (
              <Button
                variant="outline"
                render={<Link href="/futures" />}
                className="h-11 px-5 font-semibold"
              >
                Change path
              </Button>
            ) : null}
            <ThemeToggle />
          </div>
        </header>

        {!traits ? (
          <section className="mt-8 rounded-lg border bg-card p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              No trait profile yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              The plan is generated from your traits and chosen path. Take the
              twenty-question assessment first — about five minutes.
            </p>
            <Button
              render={<Link href="/assessment" />}
              className="mt-6 h-11 px-5 font-semibold"
            >
              Take the assessment
            </Button>
          </section>
        ) : !archetype ? (
          <section className="mt-8 rounded-lg border bg-card p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              No path charted yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Pick one of your three future paths and the plan will be built
              around it — its starter project, your traits, and your deadlines.
            </p>
            <Button
              render={<Link href="/futures" />}
              className="mt-6 h-11 px-5 font-semibold"
            >
              Choose a path
            </Button>
          </section>
        ) : (
          <>
            <MissionBoard archetype={archetype} traits={traits} matches={matches} />
            {matchesSettled && matches === null ? (
              <p className="mt-6 rounded-md border border-border bg-panel-raised p-3 text-sm leading-6 text-muted-foreground">
                You are signed out, so this plan has no application targets.
                <Link href="/login" className="ml-1 font-semibold text-aurora">
                  Sign in
                </Link>{" "}
                to weave your ranked opportunities and their real deadlines into
                weeks one and four.
              </p>
            ) : null}

            {/* The voyage: three legs along a dashed course, the rocket
                riding scroll from launch to arrival. */}
            <section ref={voyageRef} className="relative mt-10">
              <div
                aria-hidden
                className="absolute bottom-6 left-7 top-6 border-l border-dashed border-border"
              />
              <motion.div
                aria-hidden
                style={{ top: shipTop }}
                className="absolute left-7 z-10 -translate-x-1/2"
              >
                <Ship className="h-7 w-5 text-star" />
              </motion.div>
              {plan?.map((group, index) => (
                <div
                  key={group.timeframe}
                  className="relative flex gap-6 pb-14 last:pb-0 sm:gap-10"
                >
                  <Planet kind={LEG_PLANETS[index] ?? "moon"} />
                  <article className="min-w-0 flex-1 pt-1">
                    <p className="font-mono text-xs uppercase tracking-[0.2em] text-star">
                      {group.timeframe}
                    </p>
                    <h2 className="h-display mt-1 text-2xl text-foreground">
                      {group.focus}
                    </h2>
                    <ul className="mt-4 grid max-w-3xl gap-3">
                      {group.items.map((item) => (
                        <li
                          key={item}
                          className="flex gap-3 rounded-md border border-border bg-panel-raised p-4 text-sm leading-6 text-foreground"
                        >
                          <span className="mt-1 h-4 w-4 shrink-0 rounded border border-star" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>

                    {/* The skill rung used to dead-end. plan.ts says "run a
                        focused 5-hour sprint on statistics — the hypothesis
                        tests behind the figure you reproduced" and named no
                        course, no book, no link: an instruction only useful to
                        a student who already knew where to learn it. These are
                        free, and each was checked by fetching the page — not a
                        trial, not free-to-audit-pay-for-the-certificate.
                        Gentlest entry point first. */}
                    {index === 1 && resources.length > 0 ? (
                      <div className="mt-5 max-w-3xl rounded-md border border-border bg-card p-5">
                        <p className="font-mono text-xs uppercase tracking-[0.18em] text-star">
                          Where to learn it — free
                        </p>
                        <p className="mt-2 text-sm leading-6 text-muted-foreground">
                          {resources[0].skill_label}
                        </p>
                        <ul className="mt-4 grid gap-3">
                          {resources.map((r) => (
                            <li key={r.id}>
                              <a
                                href={r.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block rounded-md border border-border bg-panel-raised p-4 transition-colors hover:border-primary"
                              >
                                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                                  <span className="text-sm font-semibold text-foreground">
                                    {r.title}
                                  </span>
                                  <span className="font-mono text-xs text-muted-foreground">
                                    {r.kind} · {r.effort}
                                  </span>
                                </div>
                                <p className="mt-1 text-xs text-muted-foreground">
                                  {r.host}
                                </p>
                                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                                  {r.why_this_one}
                                </p>
                                {r.prerequisite &&
                                r.prerequisite.toLowerCase() !== "none" ? (
                                  <p className="mt-2 text-xs leading-5 text-aurora-dim">
                                    First: {r.prerequisite}
                                  </p>
                                ) : null}
                              </a>
                            </li>
                          ))}
                        </ul>
                        <p className="mt-4 text-xs leading-5 text-muted-foreground">
                          Every one of these is free to finish — no trial, no
                          certificate fee. We checked each page rather than
                          taking the word of a link.
                        </p>
                      </div>
                    ) : null}
                  </article>
                </div>
              ))}
            </section>
          </>
        )}
      </div>
    </main>
  );
}
