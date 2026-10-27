"use client";

/**
 * 30-day plan, generated, not hardcoded.
 *
 * The plan is assembled by lib/plan.ts from the chosen future path, the trait
 * profile, and (when signed in) the student's real ranked matches with their
 * deadlines. Signed out, the plan still generates from path + traits and says
 * plainly what signing in would add.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PathwayMap } from "@/components/PathwayMap";
import { RoadmapTree } from "@/components/RoadmapTree";
import { buildRoadmapTree, firstActionable } from "@/lib/roadmap-graph";
import { Planet } from "@/components/decor/voyage";
import {
  autoGenerateSpine,
  branchStep,
  completeSubStep,
  fetchMatches,
  fetchResources,
  fetchRoadmap,
  type BranchStep,
} from "@/lib/api";
import { SpineControl } from "@/components/SpineControl";
import { SubSteps } from "@/components/SubSteps";
import type { LearningResource, Roadmap } from "@/lib/api";
import { MissionBoard } from "@/components/MissionBoard";
import { findArchetype, generatePlan, skillKeyFor } from "@/lib/plan";
import { pathLabel, rankArchetypes, scoreTraits } from "@/lib/scoring";
import type { MatchResult } from "@/lib/types";
import { useStoredAnswers } from "@/lib/use-assessment";
import { useChosenPath } from "@/lib/use-chosen-path";
import { useRequireAuth } from "@/lib/use-require-auth";
import { AppNav } from "@/components/AppNav";
import { SpriteSky } from "@/components/decor/sprite-sky";
import { LoadingSection } from "@/components/decor/orbit-loader";

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
 * 'window' and 'eligibility' come from a deadline or a grade range, they are
 * checkable. These three are claims about how students get from one thing to
 * the next, backed by 24 hand-written spines and zero logged outcomes, so the
 * copy says "a common route" and never "required".
 */
const AUTHORED_EDGES = ["artifact", "ladder", "evidence"];

export default function PlanPage() {
  const answers = useStoredAnswers();
  const chosen = useChosenPath();
  // Built from this student's own assessment, so it needs an account.
  // Signed out this used to render a heading and an empty shell while the
  // API answered 401, gated and broken look identical from there.
  useRequireAuth();
  const [matches, setMatches] = useState<MatchResult[] | null>(null);
  const [matchesSettled, setMatchesSettled] = useState(false);
  // Free material for this path's skill rung. Additive: the plan renders
  // without it, because the step itself is still a real instruction.
  const [resources, setResources] = useState<LearningResource[]>([]);
  // The sequenced roadmap from the backend. null while loading, or when signed
  // out / unreachable, in which case the client-side generatePlan() below
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
        // Signed out or backend unreachable, the plan generates without
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
  /**
   * A student who answered "none of these are me" on /futures.
   *
   * They have charted something, a direction without a career label, and
   * findArchetype("") returns null, so the !archetype guard below used to send
   * them straight to "No path charted yet" and tell them to go and pick one of
   * the three they had just declined. Their plan comes from the generated
   * spine instead: written from their traits, grade, fields and real matched
   * opportunities, with no archetype needed.
   */
  const broad = chosen?.kind === "broad";
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

  /**
   * Ask for a first path when nobody ever wrote one.
   *
   * A plan is learn -> build -> publish -> apply, and the middle two come from
   * a spine that only arrived by charting a path on /futures. A student who
   * never went there got three application steps and a cold email, no project
   * at all, which is the one thing this product exists to tell them.
   *
   * Fires at most once per mount, and the server refuses anything beyond three
   * per student per thirty days, so a profile the model keeps declining cannot
   * retry on every page load. Silent on failure: they did not ask for this.
   */
  /**
   * Sub-steps, keyed by the step they were asked for.
   *
   * Held here rather than in the tree so one state owns them: the tree draws
   * them as branches and the step list below renders them as text, and those
   * two must never disagree about what the student asked for.
   */
  const [localBranches, setLocalBranches] = useState<Record<string, BranchStep[]>>({});
  /**
   * What the server has saved, with anything asked for in this tab on top.
   * Local wins because it is newer: the endpoint persists before it answers,
   * so a breakdown generated here is already the stored row, and a roadmap
   * response fetched before that write must not paint over it.
   */
  const branches = useMemo(
    () => ({ ...(roadmap?.branches ?? {}), ...localBranches }),
    [roadmap?.branches, localBranches],
  );
  const [branching, setBranching] = useState<string | null>(null);
  const [branchError, setBranchError] = useState<Record<string, string>>({});

  async function breakDown(step: { step_key: string; title: string; category: string }) {
    setBranching(step.step_key);
    setBranchError((e) => ({ ...e, [step.step_key]: "" }));
    try {
      const steps = await branchStep({
        stepKey: step.step_key,
        stepTitle: step.title,
        stepCategory: step.category,
      });
      setLocalBranches((current) => ({ ...current, [step.step_key]: steps }));
      setSavedAt(Date.now());
    } catch (caught) {
      // Every refusal from that endpoint is one to read: out of allowance,
      // out of budget, model unreachable, or a breakdown that tried to put an
      // unverified link or programme in the plan. The plan is unchanged in
      // all of them, which is worth saying rather than failing silently.
      setBranchError((e) => ({
        ...e,
        [step.step_key]:
          caught instanceof Error ? caught.message : "Could not break that down just now.",
      }));
    } finally {
      setBranching(null);
    }
  }

  /**
   * Ticking a sub-step.
   *
   * Optimistic, then reconciled with what the server wrote back. A checkbox
   * that waits on a round trip before it moves feels broken, and this write
   * costs nothing -- no model call, no allowance. On failure the box goes
   * back, because showing a tick that did not persist is the one outcome
   * worse than a slow one.
   */
  async function toggleSubStep(stepKey: string, index: number, done: boolean) {
    const before = branches[stepKey];
    if (!before) return;
    const after = before.map((s, i) => (i === index ? { ...s, done } : s));
    setLocalBranches((current) => ({ ...current, [stepKey]: after }));
    try {
      const saved = await completeSubStep({ stepKey, index, done });
      setLocalBranches((current) => ({ ...current, [stepKey]: saved }));
    } catch {
      setLocalBranches((current) => ({ ...current, [stepKey]: before }));
    }
  }

  /**
   * "Saved" only ever appears after the server said so.
   *
   * The sub-steps persist and always did, but silently, so a student had no
   * reason to believe the page would still know tomorrow. This is the only
   * thing that says it, which means it must never be optimistic.
   */
  const [savedAt, setSavedAt] = useState(0);
  useEffect(() => {
    if (!savedAt) return;
    const timer = setTimeout(() => setSavedAt(0), 4000);
    return () => clearTimeout(timer);
  }, [savedAt]);

  const askedForSpine = useRef(false);
  useEffect(() => {
    let live = true;
    (async () => {
      let data = await fetchRoadmap().catch(() => null);

      if (live && data && !data.has_spine && !askedForSpine.current) {
        askedForSpine.current = true;
        const written = await autoGenerateSpine();
        // Only pay for a second roadmap fetch when something actually changed.
        if (live && written.generated) {
          data = (await fetchRoadmap().catch(() => data)) ?? data;
        }
      }

      if (!live) return;
      setRoadmap(data);
      setRoadmapSettled(true);
    })();
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

  /**
   * The route, as a tree.
   *
   * Flattened out of the phases on purpose: a phase is a time bucket, and the
   * tree is about dependency, which crosses buckets. A prep step placed a hair
   * before its application (roadmap.py) can land in the phase above it, and
   * the gate must still be drawn attached to the thing it unlocks.
   *
   * Colour comes from the matched opportunity's own field, so an application
   * node is the same colour here as it is on the map and in the field sky -
   * and a step we cannot colour honestly is left on the default.
   */
  const fieldById = new Map(
    (matches ?? []).map((match) => [match.opportunity.id, match.opportunity.field]),
  );
  const tree = roadmap
    ? buildRoadmapTree(
        roadmap.phases.flatMap((phase) => phase.steps),
        { fieldOf: (id) => fieldById.get(id), horizon: roadmap.horizon, branches },
      )
    : null;

  return (
    <main className="bleed-root relative min-h-screen px-6 py-8 sm:px-8">
      {/* The same sky the landing page has. /plan is where a student spends
          the most time and it was the flattest surface in the product; the
          planets in the roadmap tree were floating on nothing. Fixed and
          behind everything, so it parallaxes without moving the content. */}
      <SpriteSky className="fixed inset-0 -z-10" />
      <div className="mx-auto max-w-5xl">
        <AppNav homeHref="/dashboard"
          right={
            <>
              {archetype || broad ? (
                <Button
                  variant="outline"
                  render={<Link href="/futures" />}
                  className="h-11 px-5 font-semibold"
                >
                  {broad ? "Pick a path instead" : "Change path"}
                </Button>
              ) : null}
            </>
          }
         />

        <header className="pb-6">
            <Link href="/futures" className="text-sm font-semibold text-aurora">
              Back to futures
            </Link>
            <h1 className="h-display mt-3 text-title text-foreground">
              30-day plan
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
              {archetype && chosen
                ? `Built from your ${pathLabel(chosen.kind).toLowerCase()} — ${
                    archetype.label
                  }${fit !== null ? ` (${fit}% fit)` : ""} — your trait profile, and your ranked matches.`
                : broad
                  ? "Built from your trait profile, the fields you lean toward, and the opportunities open to you now. No career label attached."
                  : "A concrete action list that turns a future path into visible progress within one month."}
            </p>
        </header>

        {/* The plan waits on three fetches, matches, the roadmap, and the
            resources for its skill rung. Until this, the page rendered its
            header and then a blank stretch for about three seconds, which
            reads as "there is nothing here" rather than "this is coming", and
            is the difference between a student waiting and a student leaving.

            Gated on roadmapSettled rather than on roadmap being non-null: a
            signed-out student has no roadmap and never will, and they should
            fall through to the client-side plan immediately instead of
            watching a spinner that can never resolve. */}
        {traits && !roadmapSettled ? (
          <LoadingSection
            label={
              askedForSpine.current
                ? "Writing your first project from your matches and your grade..."
                : "Building your plan from your matches and your grade..."
            }
          />
        ) : !traits ? (
          <section className="mt-8 rounded-lg border bg-card p-8 text-center">
            <h2 className="h-display text-section text-foreground">
              No trait profile yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              The plan is generated from your traits and chosen path. Take the
              twenty-question assessment first. It takes about five minutes.
            </p>
            <Button
              render={<Link href="/assessment" />}
              className="mt-6 h-11 px-5 font-semibold"
            >
              Take the assessment
            </Button>
          </section>
        ) : !archetype && !broad ? (
          <section className="mt-8 rounded-lg border bg-card p-8 text-center">
            <h2 className="h-display text-section text-foreground">
              No path charted yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Pick one of your three future paths and the plan will be built
              around it: its starter project, your traits, and your deadlines.
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
            {/* Missions are written per archetype (public.missions is keyed by
                archetype_id), so a student who declined a career label has none
               , and inventing a set for them would be the label arriving
                through the back door. Their build and publish steps come from
                the generated spine in the roadmap below instead. */}
            {archetype ? (
              <MissionBoard archetype={archetype} traits={traits} matches={matches} />
            ) : null}
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

            {/* THE MAP, before the list.
                One solar system per phase, one world per step, the rocket
                parked on the first step not yet done. A student who opens this
                page should be able to see where they are before reading
                anything, the detailed cards below are the same steps, in the
                same order, with the reasons attached.

                Completion state is not wired yet: roadmap_steps has no
                completed_at column, so nothing is marked done and the rocket
                sits on step one. That is honest rather than decorative, a map
                that claimed progress it cannot observe would be worse than one
                that shows the start. */}
            {tree && tree.nodes.length > 1 ? (
              <section className="mt-10 border-y border-border py-8">
                <p className="eyebrow">Your route</p>
                <h2 className="h-display mt-2 text-xl text-foreground">
                  What unlocks what.
                </h2>
                <p className="mt-2 max-w-2xl text-sm leading-7 text-muted-foreground">
                  The trunk is the work that compounds: learn it, build with it,
                  put it somewhere people can see. The branches are work nothing
                  is stopping you starting today. The columns at the bottom are
                  the programmes this is all for, each with the thing that gets
                  you in stacked above it. Tap any node to jump to its step.
                </p>
                <p className="mt-2 max-w-2xl text-sm leading-7 text-muted-foreground">
                  The learn steps come off{" "}
                  <Link href="/learn" className="font-semibold text-aurora">
                    the shelf
                  </Link>
                  , which has more on it than your path happens to name.
                </p>
                <RoadmapTree
                  className="mt-6"
                  tree={tree}
                  hereKey={firstActionable(tree)}
                  onBreakDown={breakDown}
                  branching={branching}
                  branches={branches}
                />
              </section>
            ) : null}

            {/* Travelling together. The matcher behind /teamup already pairs on
                chosen_archetype, chosen_kind and field_scores, the same signals
                that built this plan, so the students it surfaces are on this
                journey, not merely on this website. It was reachable only from
                the nav, which is why nobody used it. */}
            <section className="relative mt-10">
              {/* THE ROADMAP. This replaced a list of plain strings that
                  generatePlan() built client-side. Steps now come from
                  GET /roadmap, which sequences four kinds of work, learn,
                  build, publish, apply, on the student's grade progression
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
                              /* The tree above links here. scroll-mt keeps the
                                 card clear of the sticky nav after the jump. */
                              id={`step-${step.step_key}`}
                              className="scroll-mt-24 rounded-md border border-border bg-panel-raised p-4 target:border-star"
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
                              {/* BREAK THIS DOWN.
                                  The plan could be accepted whole or
                                  regenerated whole and nothing in between,
                                  which is no use to a student looking at
                                  "build a web app that calculates break-even"
                                  with no idea what the first hour of that is.
                                  The sub-steps draw as branches on the tree
                                  above and read as text here. */}
                              <SubSteps
                                stepKey={step.step_key}
                                title={step.title}
                                category={step.category}
                                branches={branches}
                                branching={branching}
                                branchError={branchError}
                                onBreakDown={breakDown}
                                onToggle={toggleSubStep}
                                depth={0}
                              />
                              {step.edge_note ? (
                                /* The overprint. A step whose edge is an
                                   authored generalisation rather than a
                                   computed calendar fact is marked the way a
                                   chart marks advice: magenta with a rule
                                   under it, so the signal survives for anyone
                                   who cannot see the colour. See the note on
                                   --advisory in app/globals.css. */
                                <p
                                  className={
                                    AUTHORED_EDGES.includes(step.edge_reason)
                                      ? "advisory mt-2 text-xs leading-5"
                                      : "mt-2 text-xs leading-5 text-muted-foreground"
                                  }
                                >
                                  {step.edge_note}
                                  {AUTHORED_EDGES.includes(step.edge_reason) ? (
                                    <span className="opacity-80">
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

              {/* Only with a roadmap in hand: the control replaces the build and
                  publish steps rendered above it, so offering it before they
                  exist would be offering to replace nothing. */}
              {roadmap && roadmap.phases.length > 0 ? (
                <SpineControl
                  source={roadmap.spine_source ?? "authored"}
                  hollow={Boolean(roadmap.spine_hollow)}
                  onReplaced={() => {
                    // Re-fetch rather than patch the steps in place: the new
                    // spine changes the learn rung too, because its skill key
                    // selects different resources, and sequencing is the
                    // backend's job.
                    fetchRoadmap().then((fresh) => {
                      if (fresh) setRoadmap(fresh);
                    });
                  }}
                />
              ) : null}
            </section>

            {/* THE STEP LIST, under the tree rather than beside it.
                This used to carry its own dashed rail and a scroll-driven
                rocket, which was the whole picture back when the plan was a
                list. The roadmap tree above is now that picture, and two
                dotted spines on one page read as one diagram overlapping
                another. The rail is gone; the planets stay, because they are
                what tells you which phase you are reading. */}
            <section
              aria-label="Find students on the same path"
              className="mt-10 border border-border bg-panel-raised p-5"
            >
              <p className="eyebrow">Nobody does this alone</p>
              <h2 className="h-display mt-2 text-xl text-foreground">
                Other students are on this same path.
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-muted-foreground">
                Team-up matches on the same signals that built this plan: your
                path, your fields, how you work. The people it finds are working
                through the same steps you are. Compare plans, split a
                project, or just have someone to ask.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button render={<Link href="/teamup" />} className="h-10 px-5">
                  Find students on this path
                </Button>
                <Button
                  variant="outline"
                  render={<Link href="/friends" />}
                  className="h-10 px-5"
                >
                  Compare with a friend
                </Button>
              </div>
            </section>
          </>
        )}

        {/* THE SAME PLAN, DRAWN AS A SKY.
            OUTSIDE the conditional chain above, deliberately. It was inside
            it, which meant the map needed a trait profile AND a charted path
            to render -- and both of those live in THIS browser's
            localStorage. The old /map route needed only a session, so a
            student in a private window, on a second device, or after clearing
            site data went from "here is your map" to "take the assessment",
            with no route left to reach it: /map now redirects here.

            PathwayMap needs none of that. GET /pathways re-scores
            server-side from the students row and the component carries its
            own loading and empty states, so a session is the only thing it
            has ever required. Gated by useRequireAuth above, like the rest of
            the page. */}
        <section className="mt-10 border-y border-border py-8">
          <p className="eyebrow">The same plan, as a sky</p>
          <h2 className="h-display mt-2 text-xl text-foreground">
            Where these programmes actually sit.
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-muted-foreground">
            One star per field, your matches orbiting it, innermost closing
            soonest. Use the list view if you would rather read it than look at
            it &mdash; it is the same matches in the same order, and it is the
            one you can operate by keyboard.
          </p>
          <div className="mt-6">
            <PathwayMap />
          </div>
        </section>

      </div>

      {/* Says what just happened, then gets out of the way. role="status"
          rather than an alert: a screen reader should hear it at the next
          pause, not be interrupted mid-sentence by good news. */}
      {savedAt ? (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 border border-aurora-dim/50 bg-panel-raised px-4 py-2.5 text-sm text-foreground shadow-xl sm:left-auto sm:right-6 sm:translate-x-0"
        >
          <span aria-hidden="true" className="mr-2 text-aurora">
            &#10003;
          </span>
          Saved. Pick up right where you left off.
        </div>
      ) : null}
    </main>
  );
}
