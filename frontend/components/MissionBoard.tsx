"use client";

/**
 * Readiness + proof missions for the chosen path.
 *
 * Two connected panels rendered on /plan:
 *  - Readiness: the gap between what the chosen archetype demands
 *    (traits on a 0-10 scale, normalized here to 0-100) and the
 *    student's current profile, plus the deadline-bearing matched
 *    opportunities in the path's fields — the "what to do about it".
 *  - Missions: three concrete real-world tasks per path; completing one
 *    writes evidence onto the student record (POST /missions/:id/complete).
 *    Missions whose trait focus matches an open gap are labelled as
 *    closing it.
 *
 * Signed out, mission fetches 401 — the board says so instead of
 * rendering nothing.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { WaypointPath } from "@/components/decor/waypoints";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  completeMission,
  fetchMissionCompletions,
  fetchMissions,
} from "@/lib/api";
import { traitDescriptions, traitLabels, type TraitKey } from "@/lib/assessment";
import type { Archetype } from "@/lib/archetypes";
import { TRAIT_KEYS, type TraitScores } from "@/lib/scoring";
import type { MatchResult, Mission, MissionCompletion } from "@/lib/types";

export function MissionBoard({
  archetype,
  traits,
  matches,
}: {
  archetype: Archetype;
  traits: TraitScores;
  matches: MatchResult[] | null;
}) {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [completions, setCompletions] = useState<Map<string, MissionCompletion>>(
    new Map(),
  );
  const [authFailed, setAuthFailed] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchMissions(archetype.id), fetchMissionCompletions()])
      .then(([missionRows, completionRows]) => {
        if (cancelled) return;
        setMissions(missionRows);
        setCompletions(
          new Map(completionRows.map((c) => [c.mission_id, c])),
        );
      })
      .catch(() => {
        if (!cancelled) setAuthFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [archetype.id]);

  async function markComplete(mission: Mission) {
    setSavingId(mission.id);
    try {
      const completion = await completeMission(
        mission.id,
        drafts[mission.id] ?? "",
      );
      setCompletions((current) =>
        new Map(current).set(mission.id, completion),
      );
    } catch {
      // Leave the button re-pressable; the record stays honest.
    } finally {
      setSavingId(null);
    }
  }

  // Readiness: where the path demands more than the profile shows.
  const gaps = TRAIT_KEYS.map((trait: TraitKey) => ({
    trait,
    demand: archetype.traits[trait] * 10,
    current: traits[trait],
    gap: archetype.traits[trait] * 10 - traits[trait],
  }))
    .filter(({ gap }) => gap > 0)
    .sort((a, b) => b.gap - a.gap)
    .slice(0, 2);
  const gapTraits = new Set(gaps.map((g) => g.trait as string));

  // Deadline routing: matched opportunities in this path's fields with
  // real upcoming deadlines, soonest first.
  const routed = (matches ?? [])
    .filter(({ opportunity }) =>
      archetype.fields.includes(opportunity.field) && opportunity.deadline,
    )
    .map(({ opportunity }) => {
      const due = new Date(`${opportunity.deadline}T23:59:59`).getTime();
      const days = Math.ceil((due - Date.now()) / 86_400_000);
      return { opportunity, days };
    })
    .filter(({ days }) => days >= 0)
    .sort((a, b) => a.days - b.days)
    .slice(0, 2);

  return (
    <section className="mt-8 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
      <div className="rounded-lg border bg-card p-5">
        <p className="eyebrow">Readiness</p>
        {gaps.length === 0 ? (
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            Your profile already meets what this path asks across every
            trait — the missions are how you prove it.
          </p>
        ) : (
          <div className="mt-4 grid gap-4">
            {gaps.map(({ trait, demand, current }) => (
              <div key={trait}>
                <div className="mb-1 flex items-baseline justify-between gap-3">
                  <span
                    className="text-sm font-semibold text-foreground"
                    title={traitDescriptions[trait]}
                  >
                    {traitLabels[trait]}
                  </span>
                  <span className="font-mono text-xs text-muted-foreground">
                    you {current} · path asks {demand}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-panel-raised">
                  <div
                    className="h-full rounded-full bg-star"
                    style={{ width: `${Math.min(100, (current / demand) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
        {routed.length > 0 ? (
          <div className="mt-6 border-t border-border pt-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Deadlines on this path
            </p>
            <ul className="mt-2 grid gap-2">
              {routed.map(({ opportunity, days }) => (
                <li
                  key={opportunity.id}
                  className="flex items-baseline justify-between gap-3"
                >
                  <Link
                    href={`/opportunities/${opportunity.id}`}
                    title={opportunity.title}
                    className="min-w-0 truncate text-sm font-semibold text-star hover:underline"
                  >
                    {opportunity.title}
                  </Link>
                  <span className="shrink-0 font-mono text-xs text-star">
                    {days === 0 ? "today" : `${days}d`}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>

      <div className="rounded-lg border bg-card p-5">
        <p className="eyebrow">Proof missions</p>
        {!authFailed && missions.length > 0 ? (
          (() => {
            const firstOpen = missions.findIndex((m) => !completions.has(m.id));
            return (
              <WaypointPath
                className="mt-4 max-w-xs"
                ariaLabel={`Mission progress: ${completions.size} of ${missions.length} complete`}
                steps={missions.map((m, i) => ({
                  label: String(i + 1).padStart(2, "0"),
                  state: completions.has(m.id)
                    ? "done"
                    : i === firstOpen
                      ? "current"
                      : "upcoming",
                }))}
              />
            );
          })()
        ) : null}
        {authFailed ? (
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            Missions write evidence to your student record, so they need a
            session —{" "}
            <Link href="/login" className="font-semibold text-star underline">
              sign in
            </Link>{" "}
            to see the three for this path.
          </p>
        ) : (
          <div className="mt-4 grid gap-4">
            {missions.map((mission) => {
              const done = completions.get(mission.id);
              const closesGap = gapTraits.has(mission.trait_focus);
              return (
                <article
                  key={mission.id}
                  className="rounded-md border border-border p-4"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h3 className="text-base font-semibold text-foreground">
                      {done ? "✓ " : ""}
                      {mission.title}
                    </h3>
                    <span className="font-mono text-[11px] uppercase tracking-wider text-aurora">
                      {traitLabels[mission.trait_focus as TraitKey] ??
                        mission.trait_focus}
                      {" · "}
                      {mission.effort}
                      {closesGap ? " · closes a gap" : ""}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {mission.description}
                  </p>
                  {done ? (
                    <p className="mt-3 font-mono text-xs text-star">
                      completed
                      {done.evidence ? ` — ${done.evidence}` : ""}
                    </p>
                  ) : (
                    <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                      <Input
                        value={drafts[mission.id] ?? ""}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [mission.id]: event.target.value,
                          }))
                        }
                        placeholder="Evidence link or one line of proof"
                        className="h-10 flex-1 bg-panel-raised px-3 text-sm"
                      />
                      <Button
                        onClick={() => markComplete(mission)}
                        disabled={savingId === mission.id}
                        className="h-10 shrink-0 px-4"
                      >
                        {savingId === mission.id ? "Saving..." : "Mark complete"}
                      </Button>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
