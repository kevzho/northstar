"use client";

/**
 * Three-step student onboarding flow (PROMPTS.md #6, Day 3).
 *
 * Step 1: identity basics (name, grade).
 * Step 2: interests (multi-select chips) + open-ended goal statement.
 * Step 3: background + IRB-style consent checkbox.
 */

import { Button } from "@/components/ui/button";
import { AppNav } from "@/components/AppNav";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { NativeSelect } from "@/components/ui/native-select";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { saveStudentProfile, syncAssessmentProfile } from "@/lib/api";
import { isComplete, scoreFieldInterests, scoreTraits } from "@/lib/scoring";
import { useStoredAnswers } from "@/lib/use-assessment";
import type { Audience, LocationPref } from "@/lib/types";

const subjectOptions = [
  "Computer Science",
  "Biology",
  "Mathematics",
  "Physics",
  "Engineering",
  "Interdisciplinary",
  "Design",
  "Business",
  "Humanities",
  "Health",
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  // The quiz is part of onboarding: brand-new students continue into it,
  // and students who took it before signing up skip straight to the
  // dashboard with their stored answers attached to the account.
  const answers = useStoredAnswers() ?? {};
  const quizDone = isComplete(answers);

  const [name, setName] = useState("");
  const [audience, setAudience] = useState<Audience>("high_school");
  const [locationPref, setLocationPref] =
    useState<LocationPref>("either");
  const [grade, setGrade] = useState("");
  const [interests, setInterests] = useState<string[]>([]);
  const [goals, setGoals] = useState("");
  const [background, setBackground] = useState("");
  const [consent, setConsent] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function toggleInterest(value: string) {
    setInterests((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    );
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      await saveStudentProfile({
        name,
        grade,
        interests,
        goals,
        audience,
        location_pref: locationPref,
        onboarded: true,
        consent,
      });
    } catch (err) {
      // Surface the failure but don't trap the user — the profile was
      // already created (with empty fields) by the dashboard. They can
      // edit it later from the dashboard.
      console.warn("onboarding save failed:", err);
    } finally {
      setIsSubmitting(false);
    }
    void background;
    if (quizDone) {
      // Taken anonymously before the account existed: the finish-time
      // sync on /assessment failed silently while signed out, so attach
      // the scores now that there is a student row to put them on.
      syncAssessmentProfile(
        scoreTraits(answers),
        scoreFieldInterests(answers),
      ).catch(() => {});
      router.push("/dashboard");
    } else {
      router.push("/assessment");
    }
  }

  const canContinue =
    (step === 1 && name.trim().length > 0 && grade.length > 0) ||
    (step === 2 && interests.length > 0 && goals.trim().length > 0) ||
    (step === 3 && background.trim().length > 0 && consent);

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <AppNav
          right={
            <p className="font-mono text-sm uppercase tracking-[0.16em] text-muted-foreground">
              Step {step} of 3
            </p>
          }
        />

        <div className="mt-10">
          <p className="eyebrow">Onboarding</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            Tell Northstar where you are.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
            A short intake that powers your opportunity recommendations. You can
            edit any of this later.
          </p>
        </div>

        <section className="rounded-lg border bg-card mt-8 p-6">
          {step === 1 ? (
            <div className="grid gap-5">
              <div className="grid gap-2">
                <span className="text-sm font-semibold text-foreground">
                  I am in...
                </span>
                <div className="flex gap-2">
                  {(
                    [
                      ["high_school", "High school"],
                      ["college", "College"],
                    ] as const
                  ).map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      aria-pressed={audience === value}
                      onClick={() => {
                        setAudience(value);
                        setGrade("");
                      }}
                      className={
                        audience === value
                          ? "border border-foreground bg-foreground px-4 py-2 text-sm font-medium text-background"
                          : "border border-border bg-transparent px-4 py-2 text-sm font-medium text-foreground"
                      }
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid gap-2">
                <span className="text-sm font-semibold text-foreground">
                  Opportunities from...
                </span>
                <div className="flex flex-wrap gap-2">
                  {(
                    [
                      ["us", "US-based"],
                      ["international", "International"],
                      ["either", "Either"],
                    ] as const
                  ).map(([value, label]) => (
                    <button
                      key={value}
                      type="button"
                      aria-pressed={locationPref === value}
                      onClick={() => setLocationPref(value)}
                      className={
                        locationPref === value
                          ? "border border-foreground bg-foreground px-4 py-2 text-sm font-medium text-background"
                          : "border border-border bg-transparent px-4 py-2 text-sm font-medium text-foreground"
                      }
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-foreground">
                  Name
                </span>
                <Input
                  type="text"
                  required
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  className="h-12 bg-panel-raised px-4 text-base"
                  placeholder="Your name"
                />
              </label>
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-foreground">
                  Grade
                </span>
                <NativeSelect
                  required
                  value={grade}
                  onChange={(event) => setGrade(event.target.value)}
                  className="h-12 px-4 text-base"
                >
                  <option value="">
                    {audience === "college"
                      ? "Select your year"
                      : "Select your grade"}
                  </option>
                  {(audience === "college"
                    ? ["Freshman", "Sophomore", "Junior", "Senior", "Gap year"]
                    : ["8", "9", "10", "11", "12", "Gap year"]
                  ).map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </NativeSelect>
              </label>
            </div>
          ) : null}

          {step === 2 ? (
            <div className="grid gap-6">
              <div>
                <p className="text-sm font-semibold text-foreground">
                  What fields interest you?
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {subjectOptions.map((subject) => {
                    const selected = interests.includes(subject);
                    return (
                      <button
                        type="button"
                        key={subject}
                        aria-pressed={selected}
                        onClick={() => toggleInterest(subject)}
                        className={
                          selected
                            ? "rounded-md border border-star bg-star px-4 py-2 text-sm font-semibold text-on-star"
                            : "rounded-md border border-input bg-panel-raised px-4 py-2 text-sm font-semibold text-foreground transition hover:border-star"
                        }
                      >
                        {subject}
                      </button>
                    );
                  })}
                </div>
              </div>
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-foreground">
                  One sentence on what you want to do or become.
                </span>
                <Textarea
                  required
                  value={goals}
                  onChange={(event) => setGoals(event.target.value)}
                  rows={3}
                  className="bg-panel-raised px-4 py-3 text-base"
                  placeholder="e.g. I want to do computational biology research that helps patients."
                />
              </label>
            </div>
          ) : null}

          {step === 3 ? (
            <div className="grid gap-6">
              <label className="grid gap-2">
                <span className="text-sm font-semibold text-foreground">
                  Background (optional, used only for eligibility filtering)
                </span>
                <Textarea
                  required
                  value={background}
                  onChange={(event) => setBackground(event.target.value)}
                  rows={3}
                  className="bg-panel-raised px-4 py-3 text-base"
                  placeholder="e.g. First-generation student at a public high school with no STEM club."
                />
              </label>
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  required
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                  className="mt-1 h-4 w-4 rounded accent-[var(--star)]"
                />
                <span className="text-sm leading-6 text-foreground">
                  I consent to Northstar storing my profile and assessment
                  responses to personalize recommendations, in line with the
                  the IRB-style data policy for this project.
                </span>
              </label>
            </div>
          ) : null}

          <div className="mt-7 flex items-center justify-between">
            <button
              type="button"
              onClick={() => setStep((current) => (current > 1 ? (current - 1) as 1 | 2 | 3 : current))}
              className="text-sm font-semibold text-aurora disabled:opacity-50"
              disabled={step === 1}
            >
              Back
            </button>

            {step < 3 ? (
              <Button
                onClick={() => setStep((current) => (current + 1) as 2 | 3)}
                disabled={!canContinue}
                className="h-11 px-5 font-semibold"
              >
                Continue
              </Button>
            ) : (
              <Button
                type="button"
                onClick={handleSubmit}
                disabled={!canContinue || isSubmitting}
                className="h-11 px-5 font-semibold"
              >
                {isSubmitting
                  ? "Saving..."
                  : quizDone
                    ? "Finish onboarding"
                    : "Finish — take the quiz"}
              </Button>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
