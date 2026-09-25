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
import { fetchMatches, fetchResources, fetchRoadmap } from "@/lib/api";
import type { LearningResource, Roadmap } from "@/lib/api";
import { MissionBoard } from "@/components/MissionBoard";
import { findArchetype, generatePlan, skillKeyFor } from "@/lib/plan";
import { pathLabel, rankArchetypes, scoreTraits } from "@/lib/scoring";
import type { MatchResult } from "@/lib/types";
import { useStoredAnswers } from "@/lib/use-assessment";
import { useChosenPath } from "@/lib/use-chosen-path";

const LEG_PLANETS = ["moon", "ringed", "giant"] as const;

/** Step kind, as a student reads it. */
const STEP_LABEL: Record<string, string> = {
  skill: "Learn",
  project: "Build",
  outreach: "Reach out",
  application: "Apply",
};

const STEP_CHIP: Record<string, string> = {
  skill: "rounded border border-input bg-panel px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-aurora",
  project: "rounded border border-input bg-panel px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-aurora",
  outreach: "rounded border border-input bg-panel px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-aurora",
  application: "rounded border border-polaris/40 bg-panel px-2 py-0.5 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-polaris",
};

/**
 * Edge reasons that are authored generalisations rather than computed facts.
 *
 * 'window' and 'eligibility' come from a deadline or a grade range — they are
 * checkable. These three are claims about how students get from one thing to
 * the next, backed by 24 hand-written spines and zero logged outcomes, so the
 * copy says "a common route" and never "required".
 */
const AUTHORED_EDGES = ["artifact", "ladder", "evidence"];

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
  // The sequenced roadmap from the backend. null while loading, or when signed
  // out / unreachable — in which case the client-side generatePlan() below
  // still renders something, minus the application steps.
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [roadmapSettled, setRoadmapSettled] = useState(false);

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

  useEffect(() => {
    let live = true;
    fetchRoadmap()
      .then((data) => {
        if (live) setRoadmap(data);
      })
      .finally(() => {
        if (live) setRoadmapSettled(true);
      });
    return () => {
      live = false;
    };
  }, [chosen?.archetypeId]);
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
              {/* THE ROADMAP. This replaced a list of plain strings that
                  generatePlan() built client-side. Steps now come from
                  GET /roadmap, which sequences four kinds of work — learn,
                  build, publish, apply — on the student's grade progression
                  rather than on catalog deadlines. Against production only 4 of
                  61 high-school opportunities carry a usable future deadline
                  and 25 are locked above a 9th grader's grade, so a
                  deadline-anchored plan had nothing to tell a freshman.

                  generatePlan() is kept as the signed-out fallback below. */}
              {roadmap && roadmap.phases.length > 0
                ? roadmap.phases.map((phase, index) => (
                    <div
                      key={`${phase.label}-${index}`}
                      className="relative flex gap-6 pb-14 last:pb-0 sm:gap-10"
                    >
                      <Planet kind={LEG_PLANETS[index] ?? "moon"} />
                      <article className="min-w-0 flex-1 pt-1">
                        <p className="font-mono text-xs uppercase tracking-[0.2em] text-star">
                          {phase.label}
                        </p>
                        <ul className="mt-4 grid max-w-3xl gap-3">
                          {phase.steps.map((step) => (
                            <li
                              key={step.step_key}
                              className="rounded-md border border-border bg-panel-raised p-4"
                            >
                              <div className="flex flex-wrap items-center gap-2">
                                <span className={STEP_CHIP[step.category]}>
                                  {STEP_LABEL[step.category]}
                                </span>
                                {step.timeframe === "week" ? (
                                  <span className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-polaris">
                                    this week
                                  </span>
                                ) : null}
                              </div>
                              {(() => {
                                // A learning step names a free resource. Link
                                // it: the whole point of the resource catalog
                                // is that "learn statistics" now has a where.
                                const linked = step.resource_id
                                  ? resources.find((r) => r.id === step.resource_id)
                                  : undefined;
                                return linked ? (
                                  <a
                                    href={linked.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="mt-2 block text-sm leading-6 text-foreground underline decoration-border underline-offset-4 hover:decoration-primary"
                                  >
                                    {step.title}
                                    <span className="ml-2 font-mono text-xs text-muted-foreground">
                                      {linked.host} · free
                                    </span>
                                  </a>
                                ) : (
                                  <p className="mt-2 text-sm leading-6 text-foreground">
                                    {step.title}
                                  </p>
                                );
                              })()}
                              {step.edge_note ? (
                                <p className="mt-2 text-xs leading-5 text-muted-foreground">
                                  {step.edge_note}
                                  {AUTHORED_EDGES.includes(step.edge_reason) ? (
                                    <span className="text-aurora-dim">
                                      {" "}
                                      (a common route, not a requirement)
                                    </span>
                                  ) : null}
                                </p>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      </article>
                    </div>
                  ))
                : roadmapSettled
                ? plan?.map((group, index) => (
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
                  ))
                : null}

              {/* Locked programs become horizon markers instead of noise. A 9th
                  grader has 25 of 61 rows above their grade; ranking them with
                  no indication they are unreachable is what this replaces. */}
              {roadmap && roadmap.horizon.length > 0 ? (
                <div className="relative flex gap-6 pb-4 sm:gap-10">
                  <Planet kind="moon" />
                  <article className="min-w-0 flex-1 pt-1">
                    <p className="font-mono text-xs uppercase tracking-[0.2em] text-star">
                      Opens later
                    </p>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                      You are not eligible for these yet. That is what the work
                      above is for.
                    </p>
                    <ul className="mt-4 grid max-w-3xl gap-2">
                      {roadmap.horizon.map((item) => (
                        <li
                          key={item.opportunity_id}
                          className="flex flex-wrap items-baseline gap-x-3 rounded-md border border-border bg-card px-4 py-3"
                        >
                          <span className="font-mono text-xs text-polaris">
                            grade {item.opens_at_grade}
                          </span>
                          <span className="text-sm text-foreground">
                            {item.title}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </article>
                </div>
              ) : null}
            </section>
          </>
        )}
      </div>
    </main>
  );
}
