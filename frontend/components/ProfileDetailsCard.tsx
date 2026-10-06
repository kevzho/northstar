"use client";

/**
 * ProfileDetailsCard — every editable student field on one card.
 *
 * "Edit your profile" used to send students back through the onboarding
 * wizard; this card replaces that trip. It loads the saved row from /me,
 * shows all details inline, and saves the whole form in one click.
 * Renders nothing when signed out — the profile page also serves
 * anonymous quiz-takers, who have no row to edit.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import { Textarea } from "@/components/ui/textarea";
import { authedFetch, saveStudentProfile } from "@/lib/api";
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

export function ProfileDetailsCard() {
  const [loaded, setLoaded] = useState(false);
  const [name, setName] = useState("");
  const [audience, setAudience] = useState<Audience>("high_school");
  const [locationPref, setLocationPref] = useState<LocationPref>("either");
  const [grade, setGrade] = useState("");
  const [interests, setInterests] = useState<string[]>([]);
  const [goals, setGoals] = useState("");
  const [socials, setSocials] = useState<Record<string, string>>({});
  const [state, setState] = useState<"idle" | "saving" | "saved" | "failed">(
    "idle",
  );

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const me = await (await authedFetch("/me")).json();
        if (!mounted) return;
        setName(me.name ?? "");
        setAudience(me.audience ?? "high_school");
        setLocationPref(me.location_pref ?? "either");
        setGrade(me.grade ?? "");
        setInterests(Array.isArray(me.interests) ? me.interests : []);
        setGoals(me.goals ?? "");
        setSocials(me.social_links ?? {});
        setLoaded(true);
      } catch {
        // Signed out or no row yet — the card simply doesn't render.
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  function toggleInterest(value: string) {
    setInterests((current) =>
      current.includes(value)
        ? current.filter((item) => item !== value)
        : [...current, value],
    );
  }

  async function save() {
    setState("saving");
    try {
      await saveStudentProfile({
        name: name.trim() || null,
        grade: grade || null,
        interests,
        goals: goals.trim() || null,
        audience,
        location_pref: locationPref,
        onboarded: true,
        social_links: socials,
      });
      setState("saved");
    } catch {
      setState("failed");
    }
  }

  if (!loaded) return null;

  return (
    <section className="rounded-lg border bg-card mt-8 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="h-display text-section text-foreground">Your details</h2>
        <Button
          variant="outline"
          render={<Link href="/dashboard" />}
          className="h-9 px-4"
        >
          Open dashboard →
        </Button>
      </div>

      <div className="mt-5 grid gap-5 sm:grid-cols-2">
        <label className="grid gap-2">
          <span className="text-sm font-semibold text-foreground">Name</span>
          <Input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Your name"
            className="h-11 bg-panel-raised px-3"
          />
        </label>
        <label className="grid gap-2">
          <span className="text-sm font-semibold text-foreground">
            {audience === "college" ? "Year" : "Grade"}
          </span>
          <NativeSelect
            value={grade}
            onChange={(event) => setGrade(event.target.value)}
            className="h-11 px-3"
          >
            <option value="">
              {audience === "college" ? "Select your year" : "Select your grade"}
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

      <div className="mt-5 grid gap-2">
        <span className="text-sm font-semibold text-foreground">I am in...</span>
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

      <div className="mt-5 grid gap-2">
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

      <div className="mt-5">
        <span className="text-sm font-semibold text-foreground">
          Fields that interest you
        </span>
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

      <label className="mt-5 grid gap-2">
        <span className="text-sm font-semibold text-foreground">Goals</span>
        <Textarea
          value={goals}
          onChange={(event) => setGoals(event.target.value)}
          placeholder="What do you want out of the next two years?"
        />
      </label>

      <div className="mt-5">
        <span className="text-sm font-semibold text-foreground">Links</span>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          Shown on your public record only — and only if you made it public.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {(
            [
              ["github", "GitHub"],
              ["website", "Personal site / portfolio"],
              ["youtube", "YouTube"],
              ["linkedin", "LinkedIn"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="grid gap-1.5">
              <span className="text-xs font-semibold text-muted-foreground">
                {label}
              </span>
              <Input
                value={socials[key] ?? ""}
                onChange={(event) =>
                  setSocials((current) => ({
                    ...current,
                    [key]: event.target.value,
                  }))
                }
                placeholder={key === "github" ? "github.com/you" : "https://…"}
                className="h-10 bg-panel-raised px-3 font-mono text-sm"
              />
            </label>
          ))}
        </div>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <Button
          onClick={save}
          disabled={state === "saving"}
          className="h-10 px-5"
        >
          {state === "saving" ? "Saving..." : "Save details"}
        </Button>
        {state === "saved" ? (
          <span className="text-sm text-muted-foreground">
            Saved — your matches will use the new details.
          </span>
        ) : state === "failed" ? (
          <span className="text-sm text-destructive">
            Saving failed — try again.
          </span>
        ) : null}
      </div>
    </section>
  );
}
