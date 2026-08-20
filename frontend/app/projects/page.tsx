"use client";

/**
 * Project recommendations.
 *
 * Real GitHub repositories worth contributing to, ranked per field by the
 * backend (GET /projects, app/projects.py). The fields come from the
 * quiz's field-interest scores — the same signal that personalizes
 * /futures — so a math-leaning student sees math repos, not a generic
 * trending list. Every card shows the score's reasons, matching the
 * "every score is a sum you can check" rule.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AppNav } from "@/components/AppNav";
import { fetchProjects } from "@/lib/api";
import { leadingFields, scoreFieldInterests } from "@/lib/scoring";
import { useStoredAnswers } from "@/lib/use-assessment";
import type { ProjectRec } from "@/lib/types";
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

export default function ProjectsPage() {
  const answers = useStoredAnswers();
  const [projects, setProjects] = useState<ProjectRec[] | null>(null);
  const [failed, setFailed] = useState(false);

  const quizFields = answers ? leadingFields(scoreFieldInterests(answers)) : [];

  useEffect(() => {
    let mounted = true;
    // answers === null both before hydration and with no stored quiz;
    // either way the fallback field set is fine to fetch with.
    const fields = answers
      ? leadingFields(scoreFieldInterests(answers))
      : ["interdisciplinary" as const];
    fetchProjects(fields)
      .then((result) => {
        if (mounted) setProjects(result);
      })
      .catch(() => {
        if (mounted) {
          setProjects([]);
          setFailed(true);
        }
      });
    return () => {
      mounted = false;
    };
  }, [answers]);

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
          <p className="eyebrow">Build something real</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            Projects for you
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
            {quizFields.length > 0
              ? `Open-source repositories matched to your leading fields (${quizFields
                  .map((field) => fieldLabels[field] ?? field)
                  .join(", ")}) — every one has open good-first-issues waiting.`
              : "Open-source repositories with open good-first-issues. Take the assessment to focus this list on your fields."}
          </p>
        </header>

        {projects === null ? (
          <LoadingSection label="Searching GitHub..." />
        ) : projects.length === 0 ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="h-display text-2xl text-foreground">
              {failed ? "Sign in to see projects" : "Nothing found right now"}
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-base leading-7 text-muted-foreground">
              {failed
                ? "Project recommendations come from the Northstar backend, which needs you signed in."
                : "GitHub's search came back empty — try again in a minute."}
            </p>
            {failed ? (
              <Button
                render={<Link href="/login" />}
                className="mt-6 h-11 px-5"
              >
                Sign in
              </Button>
            ) : null}
          </section>
        ) : (
          <div className="mt-8 grid gap-4">
            {projects.map((project) => (
              <article
                key={project.repo.full_name}
                className="rounded-lg border bg-card p-5"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <a
                    href={project.repo.html_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-lg font-semibold text-foreground underline-offset-4 hover:underline"
                  >
                    {project.repo.full_name}
                  </a>
                  <span className="badge-fit">
                    {Math.round(project.score * 100)} fit
                  </span>
                </div>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
                  {project.repo.description}
                </p>
                <p className="mt-3 font-mono text-xs tracking-wide text-aurora">
                  {fieldLabels[project.field] ?? project.field}
                  {project.repo.language ? ` · ${project.repo.language}` : ""}
                  {" · "}
                  {project.explanation}
                </p>
                <div className="mt-4">
                  <Button
                    variant="outline"
                    render={
                      <a
                        href={project.repo.good_first_issues_url}
                        target="_blank"
                        rel="noreferrer"
                      />
                    }
                    className="h-9 px-4"
                  >
                    See good first issues
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
