"use client";

/**
 * Friends — the evidence record's social layer.
 *
 * Add by handle, accept requests, and compare records side by side:
 * traits, field mix, chosen path, missions completed, outcome counts.
 * Comparison is friends-only by the backend's rules; this page just
 * renders what /friends/{id}/compare allows.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { traitLabels, type TraitKey } from "@/lib/assessment";
import { findArchetype } from "@/lib/plan";
import { TRAIT_KEYS } from "@/lib/scoring";
import {
  acceptFriend,
  compareWithFriend,
  fetchFriends,
  removeFriend,
  sendFriendRequest,
  type ComparedRecord,
  type FriendEntry,
} from "@/lib/api";

function RecordColumn({ record }: { record: ComparedRecord }) {
  const archetype = record.chosen_archetype
    ? findArchetype(record.chosen_archetype)
    : null;
  const topFields = record.field_scores
    ? Object.entries(record.field_scores)
        .filter(([, share]) => share > 0)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
    : [];
  const outcomes = Object.entries(record.outcome_counts);

  return (
    <div className="rounded-lg border bg-card p-5">
      <p className="font-mono text-xs text-aurora">@{record.handle ?? "—"}</p>
      <h3 className="mt-1 text-xl font-semibold text-foreground">
        {record.name}
      </h3>
      <p className="mt-1 text-sm text-muted-foreground">
        {archetype ? `Charting: ${archetype.label}` : "No path charted yet"}
      </p>
      <div className="mt-4 grid gap-2">
        {TRAIT_KEYS.map((trait: TraitKey) => {
          const score = record.trait_scores?.[trait] ?? 0;
          return (
            <div key={trait}>
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-xs text-muted-foreground">
                  {traitLabels[trait]}
                </span>
                <span className="font-mono text-xs text-star">{score}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-panel-raised">
                <div
                  className="h-full rounded-full bg-star"
                  style={{ width: `${score}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-4 font-mono text-xs text-muted-foreground">
        {topFields.map(([field, share]) => `${field} ${share}%`).join(" · ") ||
          "no field data"}
      </p>
      <p className="mt-2 text-sm text-foreground">
        {record.missions_completed} mission
        {record.missions_completed === 1 ? "" : "s"} completed
        {outcomes.length > 0
          ? ` · ${outcomes.map(([s, n]) => `${n} ${s}`).join(", ")}`
          : ""}
      </p>
    </div>
  );
}

export default function FriendsPage() {
  const [accepted, setAccepted] = useState<FriendEntry[]>([]);
  const [pending, setPending] = useState<FriendEntry[]>([]);
  const [handle, setHandle] = useState("");
  const [note, setNote] = useState<string | null>(null);
  const [signedOut, setSignedOut] = useState(false);
  const [comparison, setComparison] = useState<{
    me: ComparedRecord;
    friend: ComparedRecord;
  } | null>(null);

  const refresh = useCallback(() => {
    fetchFriends()
      .then((data) => {
        setAccepted(data.accepted);
        setPending(data.pending);
      })
      .catch(() => setSignedOut(true));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function add() {
    setNote(null);
    try {
      const result = await sendFriendRequest(handle.trim().toLowerCase());
      setNote(
        result.status === "accepted"
          ? "Already friends."
          : "Request sent — they accept from their friends page.",
      );
      setHandle("");
      refresh();
    } catch {
      setNote("No student with that handle (they may not have set one yet).");
    }
  }

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <AppNav
          homeHref="/dashboard"
          right={
            <Link
              href="/dashboard"
              className="text-sm font-semibold text-aurora"
            >
              Back to dashboard
            </Link>
          }
        />

        <header className="mt-10">
          <p className="eyebrow">Friends</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            Compare trajectories
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
            Add friends by handle and see records side by side — traits,
            field mix, chosen paths, missions, and outcomes. Different
            shapes, not better ones.
          </p>
        </header>

        {signedOut ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              Sign in to add friends
            </h2>
            <Button render={<Link href="/login" />} className="mt-6 h-11 px-5">
              Go to login
            </Button>
          </section>
        ) : (
          <>
            <section className="mt-8 flex flex-col gap-2 sm:flex-row">
              <Input
                value={handle}
                onChange={(event) => setHandle(event.target.value)}
                placeholder="friend-handle"
                className="h-11 flex-1 bg-panel-raised px-3 font-mono text-sm"
              />
              <Button onClick={add} disabled={!handle.trim()} className="h-11 px-5">
                Add friend
              </Button>
              <Button
                variant="outline"
                render={<Link href="/discover" />}
                className="h-11 px-5"
              >
                Discover peers
              </Button>
            </section>
            {note ? (
              <p className="mt-2 text-sm text-muted-foreground">{note}</p>
            ) : null}

            {pending.length > 0 ? (
              <section className="mt-8">
                <h2 className="text-sm font-semibold text-foreground">Pending</h2>
                <ul className="mt-3 grid gap-2">
                  {pending.map((entry) => (
                    <li
                      key={entry.id}
                      className="rounded-lg border bg-card flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                    >
                      <span className="text-sm text-foreground">
                        {entry.name}{" "}
                        <span className="font-mono text-xs text-aurora">
                          @{entry.handle}
                        </span>{" "}
                        <span className="text-xs text-muted-foreground">
                          {entry.direction === "sent"
                            ? "— waiting on them"
                            : "— wants to connect"}
                        </span>
                      </span>
                      <span className="flex gap-2">
                        {entry.direction === "received" ? (
                          <Button
                            onClick={() =>
                              acceptFriend(entry.id).then(refresh)
                            }
                            className="h-9 px-4"
                          >
                            Accept
                          </Button>
                        ) : null}
                        <Button
                          variant="outline"
                          onClick={() => removeFriend(entry.id).then(refresh)}
                          className="h-9 px-4"
                        >
                          {entry.direction === "received" ? "Decline" : "Cancel"}
                        </Button>
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section className="mt-8">
              <h2 className="text-sm font-semibold text-foreground">Friends</h2>
              {accepted.length === 0 ? (
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  No friends yet — trade handles with someone who has a
                  Northstar record.
                </p>
              ) : (
                <ul className="mt-3 grid gap-2">
                  {accepted.map((entry) => (
                    <li
                      key={entry.id}
                      className="rounded-lg border bg-card flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                    >
                      <span className="text-sm text-foreground">
                        {entry.name}{" "}
                        <span className="font-mono text-xs text-aurora">
                          @{entry.handle}
                        </span>
                      </span>
                      <span className="flex gap-2">
                        <Button
                          onClick={() =>
                            compareWithFriend(entry.student_id)
                              .then(setComparison)
                              .catch(() => setNote("Comparison failed."))
                          }
                          className="h-9 px-4"
                        >
                          Compare
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => removeFriend(entry.id).then(refresh)}
                          className="h-9 px-4"
                        >
                          Remove
                        </Button>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {comparison ? (
              <section className="mt-8">
                <h2 className="text-sm font-semibold text-foreground">
                  Side by side
                </h2>
                <div className="mt-3 grid gap-4 md:grid-cols-2">
                  <RecordColumn record={comparison.me} />
                  <RecordColumn record={comparison.friend} />
                </div>
              </section>
            ) : null}
          </>
        )}
      </div>
    </main>
  );
}
