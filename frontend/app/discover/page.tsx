"use client";

/**
 * Discover — find students who are exploring what you're exploring.
 *
 * The interest-based on-ramp to the social layer: peers are matched by
 * shared leading fields and chosen path, shown with the reason and their
 * public record, and connectable in one click. Learning by example —
 * you can see what students like you are actually doing.
 *
 * Privacy: only students who opted their profile public appear here, and
 * only within the same audience. Everyone else is invisible.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { Button } from "@/components/ui/button";
import { findArchetype } from "@/lib/plan";
import { fetchDiscover, sendFriendRequest, type Peer } from "@/lib/api";

const fieldLabels: Record<string, string> = {
  cs: "CS",
  biology: "Biology",
  math: "Math",
  physics: "Physics",
  engineering: "Engineering",
  interdisciplinary: "Interdisciplinary",
  design: "Design",
  business: "Business",
  humanities: "Humanities",
  health: "Health",
};

export default function DiscoverPage() {
  const [peers, setPeers] = useState<Peer[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [requested, setRequested] = useState<Set<string>>(new Set());

  useEffect(() => {
    let mounted = true;
    fetchDiscover()
      .then((data) => {
        if (mounted) setPeers(data);
      })
      .catch(() => {
        if (mounted) setFailed(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  function connect(peer: Peer) {
    if (!peer.handle) return;
    setRequested((current) => new Set(current).add(peer.student_id));
    sendFriendRequest(peer.handle).catch(() =>
      setRequested((current) => {
        const next = new Set(current);
        next.delete(peer.student_id);
        return next;
      }),
    );
  }

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <AppNav
          homeHref="/dashboard"
          right={
            <Link href="/friends" className="text-sm font-semibold text-aurora">
              Your friends
            </Link>
          }
        />

        <header className="mt-10">
          <p className="eyebrow">Find your people</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            Students like you
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
            Matched by the fields and paths you share — see what they&apos;re
            building, and connect. Only students who chose to be findable
            appear here.
          </p>
        </header>

        {failed ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              Sign in to discover peers
            </h2>
            <Button render={<Link href="/login" />} className="mt-6 h-11 px-5">
              Go to login
            </Button>
          </section>
        ) : peers === null ? (
          <p className="mt-10 font-mono text-sm text-muted-foreground">
            Finding students who share your interests...
          </p>
        ) : peers.length === 0 ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              No matches yet
            </h2>
            <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted-foreground">
              Take the assessment and make your profile public so others can
              find you — and check back as more students join.
            </p>
            <Button render={<Link href="/profile" />} className="mt-6 h-11 px-5">
              Make my profile findable
            </Button>
          </section>
        ) : (
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {peers.map((peer) => {
              const archetype = peer.chosen_archetype
                ? findArchetype(peer.chosen_archetype)
                : null;
              const done = requested.has(peer.student_id);
              return (
                <article
                  key={peer.student_id}
                  className="rounded-lg border bg-card p-5"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-semibold text-foreground">
                        {peer.name}
                      </h2>
                      <Link
                        href={`/p/${peer.handle}`}
                        className="font-mono text-xs text-aurora hover:underline"
                      >
                        @{peer.handle}
                      </Link>
                    </div>
                    <span className="font-mono text-xs text-muted-foreground">
                      {peer.missions_completed} mission
                      {peer.missions_completed === 1 ? "" : "s"}
                    </span>
                  </div>

                  <p className="mt-3 text-sm leading-6 text-foreground">
                    {peer.reasons.join(" · ") || "Shares your field mix"}
                  </p>
                  {archetype ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Charting: {archetype.label}
                    </p>
                  ) : null}

                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {peer.shared_fields.map((field) => (
                      <span
                        key={field}
                        className="border border-border px-2 py-0.5 font-mono text-[11px] text-muted-foreground"
                      >
                        {fieldLabels[field] ?? field}
                      </span>
                    ))}
                  </div>

                  <Button
                    onClick={() => connect(peer)}
                    disabled={done}
                    className="mt-4 h-10 px-4"
                  >
                    {done ? "Request sent" : "Connect"}
                  </Button>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
