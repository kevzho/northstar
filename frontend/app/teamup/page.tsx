"use client";

/**
 * Team up — mutual-interest collaborator and study-buddy matching.
 *
 * Not dating. The deck shows what a student is building and studying;
 * "Interested" is invisible to them unless they picked you too, at which
 * point you're connected as friends. The pool is strictly opt-in
 * (separate from the public-profile toggle), and every card carries
 * report + block.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { FieldPlanet } from "@/components/decor/field-planets";
import { ReportDialog, type ReportTarget } from "@/components/ReportDialog";
import type { OpportunityField } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { findArchetype } from "@/lib/plan";
import { LoadingSection } from "@/components/decor/orbit-loader";
import {
  fetchTeamupCandidates,
  fetchTeamupSettings,
  sendTeamupInterest,
  updateTeamupSettings,
  type TeamupCandidate,
} from "@/lib/api";
import { useRequireAuth } from "@/lib/use-require-auth";

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

const PITCH_MAX = 240;

export default function TeamupPage() {
  // Built from this student's own assessment, so it needs an account.
  // Signed out this used to render a heading and an empty shell while the
  // API answered 401 — gated and broken look identical from there.
  useRequireAuth();
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [pitch, setPitch] = useState("");
  const [signedOut, setSignedOut] = useState(false);
  const [deck, setDeck] = useState<TeamupCandidate[]>([]);
  const [deckLoaded, setDeckLoaded] = useState(false);
  const [matched, setMatched] = useState<TeamupCandidate | null>(null);
  const [reporting, setReporting] = useState<ReportTarget | null>(null);
  const [detail, setDetail] = useState<TeamupCandidate | null>(null);
  const [editingPitch, setEditingPitch] = useState(false);

  const loadDeck = useCallback(() => {
    fetchTeamupCandidates()
      .then((candidates) => {
        setDeck(candidates);
        setDeckLoaded(true);
      })
      .catch(() => setDeckLoaded(true));
  }, []);

  useEffect(() => {
    let mounted = true;
    // Both requests fire at once: for enrolled students that halves the
    // wait (the old flow loaded settings, THEN the deck). For everyone
    // else the candidates call 409s and is ignored.
    loadDeck();
    fetchTeamupSettings()
      .then((settings) => {
        if (!mounted) return;
        setEnabled(settings.enabled);
        setPitch(settings.pitch);
      })
      .catch(() => {
        if (mounted) setSignedOut(true);
      });
    return () => {
      mounted = false;
    };
  }, [loadDeck]);

  async function join() {
    try {
      const settings = await updateTeamupSettings({
        enabled: true,
        pitch: pitch.trim(),
      });
      setEnabled(settings.enabled);
      setPitch(settings.pitch);
      loadDeck();
    } catch {
      setSignedOut(true);
    }
  }

  async function leave() {
    await updateTeamupSettings({ enabled: false }).catch(() => undefined);
    setEnabled(false);
    setDeck([]);
    setDeckLoaded(false);
  }

  async function savePitch() {
    const settings = await updateTeamupSettings({ pitch: pitch.trim() });
    setPitch(settings.pitch);
    setEditingPitch(false);
  }

  function decide(candidate: TeamupCandidate, decision: "interested" | "passed") {
    setDeck((current) =>
      current.filter((c) => c.student_id !== candidate.student_id),
    );
    sendTeamupInterest(candidate.student_id, decision)
      .then((result) => {
        if (result.matched) setMatched(candidate);
      })
      .catch(() => undefined);
  }

  const candidate = deck[0];

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <AppNav
          homeHref="/dashboard"
          right={
            <Link href="/friends" className="text-sm font-semibold text-aurora">
              Your friends
            </Link>
          }
        />

        <header className="mt-10">
          <p className="eyebrow">Team up</p>
          <h1 className="h-display mt-3 text-title text-foreground">
            Find a collaborator
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
            A study buddy, a hackathon teammate, a co-founder for your science
            fair project. Pick the students you&apos;d build with — if they
            pick you too, you&apos;re connected. Nobody sees a one-sided pick.
          </p>
        </header>

        {signedOut ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="h-display text-section text-foreground">
              Sign in to team up
            </h2>
            <Button render={<Link href="/login" />} className="mt-6 h-11 px-5">
              Go to login
            </Button>
          </section>
        ) : enabled === null ? (
          <LoadingSection label="Opening the matching pool..." />
        ) : !enabled ? (
          <section className="rounded-lg border bg-card mt-10 p-8">
            <h2 className="h-display text-section text-foreground">
              Join the matching pool
            </h2>
            <ul className="mt-3 grid gap-1.5 text-sm leading-6 text-muted-foreground">
              <li>· Only students who joined can see or be seen here.</li>
              <li>· Your picks stay invisible unless they&apos;re mutual.</li>
              <li>· Report and block work on every card, and you can leave anytime.</li>
            </ul>
            <label className="mt-5 block text-xs font-semibold text-foreground">
              What are you building or studying?
              <Textarea
                value={pitch}
                onChange={(event) => setPitch(event.target.value)}
                maxLength={PITCH_MAX}
                className="mt-1.5"
                placeholder="e.g. Training a bird-call classifier for the science fair — need someone who likes data cleaning. Also prepping for AMC 12."
              />
            </label>
            <p className="mt-1 text-right font-mono text-[11px] text-muted-foreground">
              {pitch.length}/{PITCH_MAX}
            </p>
            <Button
              onClick={join}
              disabled={!pitch.trim()}
              className="mt-4 h-11 px-5"
            >
              Join with this pitch
            </Button>
          </section>
        ) : (
          <>
            {matched ? (
              <section className="mt-8 rounded-lg border border-star bg-card p-6 text-center">
                <h2 className="h-display text-section text-star">
                  It&apos;s mutual — you and {matched.name} both want to team up
                </h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  You&apos;re now connected as friends. Compare records and
                  take it from there.
                </p>
                <span className="mt-4 inline-flex gap-2">
                  <Button render={<Link href="/friends" />} className="h-10 px-4">
                    Open friends
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setMatched(null)}
                    className="h-10 px-4"
                  >
                    Keep browsing
                  </Button>
                </span>
              </section>
            ) : null}

            {!candidate ? (
              deckLoaded ? (
                <section className="rounded-lg border bg-card mt-8 p-8 text-center">
                  <h2 className="h-display text-section text-foreground">
                    No new candidates right now
                  </h2>
                  <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted-foreground">
                    You&apos;ve seen everyone in the pool. Check back as more
                    students join — or browse peers on Discover.
                  </p>
                  <Button
                    variant="outline"
                    render={<Link href="/discover" />}
                    className="mt-6 h-11 px-5"
                  >
                    Discover peers
                  </Button>
                </section>
              ) : (
                <LoadingSection label="Scanning for co-builders in your orbit…" className="mt-8 flex flex-col items-center gap-4 text-center" />
              )
            ) : (
              <section className="mt-8 rounded-lg border bg-card p-6">
                <div className="flex items-baseline justify-between gap-3">
                  <div>
                    <h2 className="h-display text-section text-foreground">
                      {candidate.name}
                    </h2>
                    {candidate.handle ? (
                      <Link
                        href={`/p/${candidate.handle}`}
                        className="font-mono text-xs text-aurora hover:underline"
                      >
                        @{candidate.handle}
                      </Link>
                    ) : null}
                  </div>
                  <span className="font-mono text-xs text-muted-foreground">
                    {candidate.grade ? `grade ${candidate.grade} · ` : ""}
                    {candidate.missions_completed} mission
                    {candidate.missions_completed === 1 ? "" : "s"}
                  </span>
                </div>

                {candidate.pitch ? (
                  <p className="mt-4 text-base leading-7 text-foreground">
                    &ldquo;{candidate.pitch}&rdquo;
                  </p>
                ) : null}

                <p className="mt-3 text-sm text-muted-foreground">
                  {candidate.reasons.join(" · ") || "A different shape than yours — sometimes that's the best teammate"}
                  {candidate.chosen_archetype && findArchetype(candidate.chosen_archetype)
                    ? ` · charting: ${findArchetype(candidate.chosen_archetype)!.label}`
                    : ""}
                </p>

                <div className="mt-3 flex flex-wrap gap-1.5">
                  {candidate.fields.map((field) => (
                    <span
                      key={field}
                      className="flex items-center gap-1 border border-border px-2 py-0.5 font-mono text-[11px] text-muted-foreground"
                    >
                      <FieldPlanet
                        field={field as OpportunityField}
                        className="h-3 w-3"
                      />
                      {fieldLabels[field] ?? field}
                    </span>
                  ))}
                </div>

                <div className="mt-6 flex flex-wrap items-center gap-2">
                  <Button
                    onClick={() => decide(candidate, "interested")}
                    className="h-11 px-6"
                  >
                    I&apos;d build with them
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => decide(candidate, "passed")}
                    className="h-11 px-5"
                  >
                    Skip
                  </Button>
                  <button
                    onClick={() => setDetail(candidate)}
                    className="ml-auto text-xs font-semibold text-aurora underline-offset-2 hover:underline"
                  >
                    Full details
                  </button>
                  <button
                    onClick={() =>
                      setReporting({
                        student_id: candidate.student_id,
                        name: candidate.name,
                        handle: candidate.handle,
                      })
                    }
                    className="text-xs text-muted-foreground underline-offset-2 hover:underline"
                  >
                    Report this profile
                  </button>
                </div>
              </section>
            )}

            <section className="mt-8 rounded-lg border bg-card px-4 py-3">
              {editingPitch ? (
                <div>
                  <Textarea
                    value={pitch}
                    onChange={(event) => setPitch(event.target.value)}
                    maxLength={PITCH_MAX}
                  />
                  <span className="mt-2 flex gap-2">
                    <Button onClick={savePitch} className="h-9 px-4">
                      Save pitch
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => setEditingPitch(false)}
                      className="h-9 px-4"
                    >
                      Cancel
                    </Button>
                  </span>
                </div>
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className="text-sm text-muted-foreground">
                    Your pitch: <span className="text-foreground">{pitch || "—"}</span>
                  </span>
                  <span className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setEditingPitch(true)}
                      className="h-9 px-4"
                    >
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      onClick={leave}
                      className="h-9 px-4"
                    >
                      Leave matching
                    </Button>
                  </span>
                </div>
              )}
            </section>
          </>
        )}

        {detail ? (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-6 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
            aria-label={`About ${detail.name}`}
            onClick={() => setDetail(null)}
          >
            <div
              className="w-full max-w-md rounded-lg border bg-card p-6"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex items-baseline justify-between gap-3">
                <h2 className="h-display text-section text-foreground">
                  {detail.name}
                </h2>
                <span className="font-mono text-xs text-muted-foreground">
                  {detail.grade ? `grade ${detail.grade}` : ""}
                </span>
              </div>
              {detail.pitch ? (
                <p className="mt-3 text-sm leading-6 text-foreground">
                  &ldquo;{detail.pitch}&rdquo;
                </p>
              ) : null}
              <dl className="mt-4 grid gap-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Charting</dt>
                  <dd className="text-foreground">
                    {detail.chosen_archetype
                      ? findArchetype(detail.chosen_archetype)?.label ??
                        "A path of their own"
                      : "No path chosen yet"}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Missions completed</dt>
                  <dd className="font-mono text-foreground">
                    {detail.missions_completed}
                  </dd>
                </div>
              </dl>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {detail.fields.map((field) => (
                  <span
                    key={field}
                    className="flex items-center gap-1 border border-border px-2 py-0.5 font-mono text-[11px] text-muted-foreground"
                  >
                    <FieldPlanet
                      field={field as OpportunityField}
                      className="h-3 w-3"
                    />
                    {fieldLabels[field] ?? field}
                  </span>
                ))}
              </div>
              <div className="mt-5 flex flex-wrap items-center gap-2">
                {detail.handle ? (
                  <Button
                    variant="outline"
                    render={<Link href={`/p/${detail.handle}`} />}
                    className="h-10 px-4"
                  >
                    View public record →
                  </Button>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    Their full record unlocks if you match.
                  </p>
                )}
                <Button
                  onClick={() => setDetail(null)}
                  className="ml-auto h-10 px-4"
                >
                  Back to the deck
                </Button>
              </div>
            </div>
          </div>
        ) : null}

        {reporting ? (
          <ReportDialog
            target={reporting}
            onClose={() => setReporting(null)}
            onBlocked={() =>
              setDeck((current) =>
                current.filter((c) => c.student_id !== reporting.student_id),
              )
            }
          />
        ) : null}
      </div>
    </main>
  );
}
