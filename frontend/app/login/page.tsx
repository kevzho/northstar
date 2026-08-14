"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState } from "react";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function signInWithGoogle() {
    setError(null);
    const origin = window.location.origin;
    const { error: authError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${origin}/auth/callback`,
      },
    });

    if (authError) {
      setError(authError.message);
    }
  }

  async function sendMagicLink(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setStatus(null);
    setIsSubmitting(true);

    const origin = window.location.origin;
    const { error: authError } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${origin}/auth/callback`,
      },
    });

    setIsSubmitting(false);

    if (authError) {
      setError(authError.message);
      return;
    }

    setStatus("Check your email for a Northstar sign-in link.");
  }

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-5xl flex-col">
        <nav className="flex items-center justify-between border-b border-border pb-5">
          <Link href="/" className="h-display text-xl text-foreground">
            Northstar
          </Link>
          <Link
            href="/"
            className="text-sm font-semibold text-aurora"
          >
            Back home
          </Link>
        </nav>

        <section className="grid flex-1 items-center gap-10 py-12 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="eyebrow">Student sign in</p>
            <h1 className="h-display mt-4 text-4xl text-foreground sm:text-5xl">
              Start with Northstar.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-8 text-muted-foreground">
              Sign in to save your assessment, trait profile, future paths, and
              30-day plan.
            </p>
          </div>

          <div className="rounded-lg border bg-card p-5 sm:p-6">
            <Button
              type="button"
              onClick={signInWithGoogle}
              className="h-12 w-full px-5 font-semibold"
            >
              Continue with Google
            </Button>

            <div className="my-6 flex items-center gap-3">
              <div className="h-px flex-1 bg-[var(--border)]" />
              <span className="font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground">
                or
              </span>
              <div className="h-px flex-1 bg-[var(--border)]" />
            </div>

            <form onSubmit={sendMagicLink} className="grid gap-3">
              <Label
                htmlFor="email"
                className="text-sm font-semibold text-foreground"
              >
                Email address
              </Label>
              <Input
                id="email"
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                className="h-12 bg-panel-raised px-4 text-base"
              />
              <Button variant="outline"
                type="submit"
                disabled={isSubmitting}
                className="mt-2 h-12 px-5 font-semibold"
              >
                {isSubmitting ? "Sending..." : "Send magic link"}
              </Button>
            </form>

            {status ? (
              <p className="mt-4 rounded-md border border-[var(--success-border)] bg-[var(--success-bg)] p-3 text-sm leading-6 text-[var(--success-text)]">
                {status}
              </p>
            ) : null}

            {error ? (
              <p className="mt-4 rounded-md border border-[var(--error-border)] bg-[var(--error-bg)] p-3 text-sm leading-6 text-[var(--error-text)]">
                {error}
              </p>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
