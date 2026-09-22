"use client";

/**
 * Mentor recommendations page.
 *
 * Lists mentors ranked by TF-IDF cosine similarity to the student's
 * interests and goals. Each card shows name, bio snippet, expertise
 * badges, match score, and the explanation from the engine.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AppNav } from "@/components/AppNav";
import { authedFetch, fetchMentors } from "@/lib/api";
import type { MentorMatch } from "@/lib/api";
import { buildIntroEmail, mailtoHref } from "@/lib/outreach";
import type { StudentProfile } from "@/lib/types";
import { LoadingSection } from "@/components/decor/orbit-loader";

export default function MentorsPage() {
  const [mentors, setMentors] = useState<MentorMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [draftFor, setDraftFor] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchMentors();
        if (!cancelled) setMentors(data);
      } catch {
        if (!cancelled) setError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
      // The profile personalizes email drafts; its absence only means the
      // draft keeps its [EDIT] placeholders.
      try {
        const response = await authedFetch("/me");
        const me = (await response.json()) as StudentProfile;
        if (!cancelled) setProfile(me);
      } catch {
        if (!cancelled) setProfile(null);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  async function copyDraft(mentorId: string, text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(mentorId);
    } catch {
      // Clipboard unavailable — the draft is still selectable text.
    }
  }

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-4xl">
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
          <p className="eyebrow">Mentors</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            Mentor recommendations
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
            Mentors who have opted in, ranked by how well their expertise
            aligns with your profile.
          </p>
        </header>

        {loading ? (
          <LoadingSection label="Finding mentors that match your profile..." />
        ) : error ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              Could not load mentors
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Your session may have expired, or the server is unreachable. This
              is not an empty directory — reload, and sign in again if that
              does not help.
            </p>
          </section>
        ) : mentors.length === 0 ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              No mentors yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              This directory is deliberately empty. It previously listed
              sample profiles that were not real people, and those have been
              removed rather than left to look like an offer we could keep.
            </p>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              It will fill with mentors who have agreed in writing to hear
              from students. Until then, every other surface in Northstar
              points at programs you can actually apply to today.
            </p>
            <Button
              render={<Link href="/opportunities" />}
              className="mt-5 h-10 px-4"
            >
              Browse opportunities
            </Button>
          </section>
        ) : (
          <section className="mt-8 grid gap-4">
            {mentors.slice(0, 5).map(({ mentor, score }) => (
              <article key={mentor.id} className="rounded-lg border bg-card p-5">
                <div className="flex items-center gap-3">
                  <span className="badge-fit">
                    {Math.round(score.score * 100)}% fit
                  </span>
                  <div>
                    <h2 className="text-lg font-semibold text-foreground">
                      {mentor.name}
                    </h2>
                    <p className="font-mono text-xs text-muted-foreground">
                      {mentor.email}
                    </p>
                  </div>
                </div>
                <p className="mt-3 text-sm leading-6 text-foreground">
                  {mentor.bio}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {mentor.expertise.map((tag) => (
                    <span
                      key={tag}
                      className="rounded border border-input bg-panel-raised px-2 py-0.5 text-xs font-medium text-aurora"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                <p className="mt-3 text-xs leading-5 text-muted-foreground italic">
                  {score.explanation}
                </p>
                <div className="mt-4">
                  <Button
                    variant="outline"
                    className="h-9 px-4 font-semibold"
                    aria-expanded={draftFor === mentor.id}
                    onClick={() =>
                      setDraftFor(draftFor === mentor.id ? null : mentor.id)
                    }
                  >
                    {draftFor === mentor.id ? "Hide draft" : "Draft intro email"}
                  </Button>
                </div>
                {draftFor === mentor.id
                  ? (() => {
                      const draft = buildIntroEmail({ mentor, score }, profile);
                      return (
                        <div className="mt-4 rounded-md border border-border bg-panel-raised p-4">
                          <p className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                            Subject
                          </p>
                          <p className="mt-1 text-sm font-semibold text-foreground">
                            {draft.subject}
                          </p>
                          <p className="mt-3 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                            Body — fill in every [EDIT] before sending
                          </p>
                          <pre className="mt-1 whitespace-pre-wrap font-sans text-sm leading-6 text-foreground">
                            {draft.body}
                          </pre>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <Button
                              className="h-9 px-4 font-semibold"
                              onClick={() =>
                                copyDraft(
                                  mentor.id,
                                  `Subject: ${draft.subject}\n\n${draft.body}`,
                                )
                              }
                            >
                              {copied === mentor.id ? "Copied" : "Copy draft"}
                            </Button>
                            <Button
                              variant="outline"
                              render={
                                <a href={mailtoHref(mentor.email, draft)} />
                              }
                              className="h-9 px-4 font-semibold"
                            >
                              Open in email app
                            </Button>
                          </div>
                        </div>
                      );
                    })()
                  : null}
              </article>
            ))}
          </section>
        )}
      </div>
    </main>
  );
}
