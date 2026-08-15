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
import { fetchMatches } from "@/lib/api";
import { MissionBoard } from "@/components/MissionBoard";
import { findArchetype, generatePlan } from "@/lib/plan";
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
              seventeen-question assessment first — about five minutes.
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
