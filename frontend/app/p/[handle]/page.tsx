"use client";

/**
 * The public evidence record — northstar.study/p/<handle>.
 *
 * Opt-in only; the backend serves highlights (trait/field shape, chosen
 * path, mission evidence, positive outcomes) and 404s uniformly for
 * private or unknown handles. This page is the product's proof artifact:
 * a shareable, verifiable trajectory — a GitHub profile for becoming
 * someone.
 */

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { Button } from "@/components/ui/button";
import { findArchetype } from "@/lib/plan";
import { fetchPublicProfile } from "@/lib/api";
import type { PublicProfile } from "@/lib/types";
import { LoadingSection } from "@/components/decor/orbit-loader";

const fieldLabels: Record<string, string> = {
  cs: "Computer science",
  biology: "Biology",
  math: "Mathematics",
  physics: "Physics",
  engineering: "Engineering",
  interdisciplinary: "Interdisciplinary",
  design: "Design & Media",
  business: "Business",
  humanities: "Humanities",
  health: "Health",
};

export default function PublicProfilePage({
  params,
}: {
  params: Promise<{ handle: string }>;
}) {
  const { handle } = use(params);
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    let mounted = true;
    fetchPublicProfile(handle)
      .then((data) => {
        if (mounted) setProfile(data);
      })
      .catch(() => {
        if (mounted) setMissing(true);
      });
    return () => {
      mounted = false;
    };
  }, [handle]);

  const archetype = profile?.chosen_archetype
    ? findArchetype(profile.chosen_archetype)
    : null;
  const orderedFields = profile?.field_scores
    ? Object.entries(profile.field_scores)
        .filter(([, share]) => share > 0)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 4)
    : [];

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <AppNav
          right={
            <Link href="/" className="text-sm font-semibold text-aurora">
              What is Northstar?
            </Link>
          }
        />

        {missing ? (
          <section className="rounded-lg border bg-card mt-16 p-8 text-center">
            <h1 className="h-display text-3xl text-foreground">
              No public record here
            </h1>
            <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted-foreground">
              This handle does not exist, or its owner keeps their record
              private.
            </p>
            <Button render={<Link href="/" />} className="mt-6 h-11 px-5">
              Explore Northstar
            </Button>
          </section>
        ) : !profile ? (
          <LoadingSection label="Loading their record..." className="mt-16 flex flex-col items-center gap-4 text-center" />
        ) : (
          <>
            <header className="mt-10">
              <p className="eyebrow">Evidence record · @{profile.handle}</p>
              <h1 className="h-display mt-3 text-title text-foreground">
                {profile.name}
              </h1>
              <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
                {archetype
                  ? `Charting toward ${archetype.label.toLowerCase()} — every step below is logged evidence, not a claim.`
                  : "Every step below is logged evidence, not a claim."}
              </p>
              {Object.keys(profile.social_links ?? {}).length > 0 ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {Object.entries(profile.social_links).map(([key, url]) => (
                    <a
                      key={key}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="border border-border px-2.5 py-1 font-mono text-xs text-aurora transition-colors hover:border-star hover:text-star"
                    >
                      {key} ↗
                    </a>
                  ))}
                </div>
              ) : null}
            </header>

            {orderedFields.length > 0 ? (
              <section className="rounded-lg border bg-card mt-8 p-5">
                <h2 className="text-note font-semibold text-foreground">
                  Field mix
                </h2>
                <div className="mt-4 grid gap-3">
                  {orderedFields.map(([field, share]) => (
                    <div key={field}>
                      <div className="mb-1 flex items-baseline justify-between gap-3">
                        <span className="text-sm text-foreground">
                          {fieldLabels[field] ?? field}
                        </span>
                        <span className="font-mono text-xs text-star">
                          {share}%
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-panel-raised">
                        <div
                          className="h-full rounded-full bg-star"
                          style={{ width: `${share}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {profile.outcomes.length > 0 ? (
              <section className="rounded-lg border bg-card mt-6 p-5">
                <h2 className="text-note font-semibold text-foreground">
                  Outcomes
                </h2>
                <ul className="mt-3 grid gap-2">
                  {profile.outcomes.map((outcome, index) => (
                    <li
                      key={index}
                      className="flex flex-wrap items-baseline gap-x-3 gap-y-1"
                    >
                      <span className="badge-fit">{outcome.status}</span>
                      <span className="text-sm font-semibold text-foreground">
                        {outcome.title}
                      </span>
                      <span className="font-mono text-xs text-muted-foreground">
                        {outcome.at?.slice(0, 10)}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {profile.missions.length > 0 ? (
              <section className="rounded-lg border bg-card mt-6 p-5">
                <h2 className="text-note font-semibold text-foreground">
                  Proof missions completed
                </h2>
                <ul className="mt-3 grid gap-3">
                  {profile.missions.map((mission, index) => (
                    <li key={index}>
                      <p className="text-sm font-semibold text-foreground">
                        ✓ {mission.title}
                      </p>
                      {mission.evidence ? (
                        <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
                          {mission.evidence}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section className="mt-10 border-t border-border pt-6 text-center">
              <p className="text-sm leading-6 text-muted-foreground">
                Records like this are built one mission and one real outcome
                at a time.
              </p>
              <Button render={<Link href="/assessment" />} className="mt-4 h-11 px-5">
                Start your own
              </Button>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
