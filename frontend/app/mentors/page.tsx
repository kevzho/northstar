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
import { fetchMentors } from "@/lib/api";
import type { MentorMatch } from "@/lib/api";

export default function MentorsPage() {
  const [mentors, setMentors] = useState<MentorMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

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
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-4xl">
        <div className="flex items-center justify-between border-b border-border pb-5">
          <Link
            href="/dashboard"
            className="h-display text-xl text-foreground"
          >
            Northstar
          </Link>
          <Link
            href="/dashboard"
            className="text-sm font-semibold text-aurora"
          >
            Back to dashboard
          </Link>
        </div>

        <header className="mt-10">
          <p className="eyebrow">Mentors</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            Mentor recommendations
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
            Ranked by how well their expertise aligns with your profile.
            Reach out to mentors you want to work with.
          </p>
        </header>

        {loading ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <p className="font-mono text-sm text-muted-foreground">
              Finding mentors that match your profile...
            </p>
          </section>
        ) : error ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              Could not load mentors
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              The mentor matching engine may not have seed data yet. Run
              scripts/seed_mentors.sql in the Supabase SQL Editor.
            </p>
          </section>
        ) : mentors.length === 0 ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              No mentors yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Mentor data has not been seeded. Run scripts/seed_mentors.sql
              to populate the catalog.
            </p>
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
              </article>
            ))}
          </section>
        )}
      </div>
    </main>
  );
}
