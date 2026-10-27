"use client";

/**
 * The way into the mentor directory. There was not one.
 *
 * `table("mentors")` appeared exactly once in the backend, the read in
 * GET /mentors, so the directory's empty state promised it "will fill with
 * mentors who have agreed in writing to hear from students" and nothing could
 * ever make that true. It was not empty for want of volunteers. There was
 * nowhere to volunteer.
 *
 * Deliberately NOT behind useRequireAuth. A teacher or researcher offering an
 * hour should not have to create a student account first; the thing standing
 * between them and the form should be nothing at all.
 *
 * What they submit does not appear anywhere a student can see it. It lands in
 * mentor_applications, which no public role can read or write, and a person
 * moves it across. The page says so plainly, because someone deciding whether
 * to put their email in front of teenagers is owed that before they type it.
 */

import Link from "next/link";
import { useState } from "react";
import { AppNav } from "@/components/AppNav";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { applyToMentor } from "@/lib/api";

const FIELDS = [
  "biology", "cs", "math", "physics", "engineering",
  "health", "business", "humanities", "design", "interdisciplinary",
] as const;

export default function MentorJoinPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [bio, setBio] = useState("");
  const [link, setLink] = useState("");
  const [expertise, setExpertise] = useState<string[]>([]);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState("");

  function toggle(field: string) {
    setExpertise((current) =>
      current.includes(field)
        ? current.filter((f) => f !== field)
        : [...current, field],
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await applyToMentor({ name, email, bio, link, expertise, consent });
      setDone(result.next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="bleed-root min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-2xl">
        <AppNav
          right={
            <Link href="/mentors" className="text-sm font-semibold text-aurora">
              Back
            </Link>
          }
        />

        <header className="mt-10">
          <p className="eyebrow">Offer to mentor</p>
          <h1 className="h-display mt-3 text-title text-foreground">
            One conversation is often the whole thing
          </h1>
          <p className="mt-4 text-lede text-muted-foreground">
            Most students who find a research programme find it because one
            person told them it existed. If you work in a STEM field, you know
            things that are not written down anywhere a 15-year-old will look.
          </p>
        </header>

        {done ? (
          <section
            aria-live="polite"
            className="mt-8 border border-border bg-card p-6"
          >
            <h2 className="h-display text-section text-foreground">Thank you — received</h2>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{done}</p>
            <Button render={<Link href="/" />} className="mt-5 h-10 px-4">
              Back to Northstar
            </Button>
          </section>
        ) : (
          <form onSubmit={submit} className="mt-8 space-y-6">
            <div>
              <Label htmlFor="m-name">Your name</Label>
              <Input id="m-name" value={name} required maxLength={120}
                onChange={(e) => setName(e.target.value)} className="mt-2" />
            </div>

            <div>
              <Label htmlFor="m-email">Email students would write to</Label>
              <Input id="m-email" type="email" value={email} required maxLength={200}
                onChange={(e) => setEmail(e.target.value)} className="mt-2" />
              <p className="mt-2 text-note text-muted-foreground">
                Shown to signed-in students as a mailto link if your application
                is approved. Use an address you are happy to publish.
              </p>
            </div>

            <div>
              <Label htmlFor="m-bio">What do you work on?</Label>
              <textarea
                id="m-bio" value={bio} required rows={5} maxLength={2000}
                onChange={(e) => setBio(e.target.value)}
                placeholder="A few sentences. This is what a student is matched against, so specifics help more than titles — &quot;I run a wet lab doing CRISPR screens and I have supervised four high schoolers&quot; beats &quot;research scientist&quot;."
                className="mt-2 w-full border border-border bg-transparent p-3 text-sm leading-6 text-foreground placeholder:text-muted-foreground focus-visible:border-foreground focus-visible:outline-none"
              />
            </div>

            <fieldset>
              <legend className="text-sm font-medium text-foreground">
                Fields you could speak to
              </legend>
              <div className="mt-3 flex flex-wrap gap-2">
                {FIELDS.map((f) => (
                  <button
                    key={f} type="button" aria-pressed={expertise.includes(f)}
                    onClick={() => toggle(f)}
                    className={
                      expertise.includes(f)
                        ? "border border-foreground bg-foreground px-3 py-2 text-note font-medium capitalize text-background"
                        : "border border-border bg-transparent px-3 py-2 text-note font-medium capitalize text-foreground"
                    }
                  >
                    {f}
                  </button>
                ))}
              </div>
            </fieldset>

            <div>
              <Label htmlFor="m-link">A page about your work (optional)</Label>
              <Input id="m-link" value={link} maxLength={300}
                onChange={(e) => setLink(e.target.value)} className="mt-2"
                placeholder="A lab page, a profile, anything that shows this is you" />
            </div>

            {/* The consent, in the words it is stored under. Someone deciding
                whether to put their address in front of minors should read the
                actual sentence, not a summary of it. */}
            <label className="flex gap-3 border border-border p-4 text-sm leading-6 text-foreground">
              <input
                type="checkbox" checked={consent} required
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-1 h-4 w-4 shrink-0"
              />
              <span>
                I am happy to be listed in Northstar&apos;s mentor directory,
                where high-school students can see my name, what I work on, and
                an email address they may write to. I understand students may
                contact me directly, that Northstar does not supervise those
                conversations, and that I can ask to be removed at any time.
              </span>
            </label>

            <p className="text-note leading-6 text-muted-foreground">
              Nothing here is published automatically. A person reads every
              application, and your name does not appear anywhere students can
              see until they have.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" disabled={busy} className="h-11 px-5 font-semibold">
                {busy ? "Sending…" : "Send application"}
              </Button>
              {error ? (
                <span aria-live="polite" className="text-sm text-foreground">
                  {error}
                </span>
              ) : null}
            </div>
          </form>
        )}
      </div>
    </main>
  );
}
