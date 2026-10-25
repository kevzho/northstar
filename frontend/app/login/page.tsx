"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AppNav } from "@/components/AppNav";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";

function LoginInner() {
  // Set by lib/use-require-auth.ts when a personal page turned someone away.
  // Saying which page, and that it was gated rather than broken, is the whole
  // reason that redirect exists — the pages used to render an empty shell and
  // leave people to guess.
  const params = useSearchParams();
  const gated = params.get("reason") === "account";
  const from = params.get("from") || "";
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Google is the steered path (no email rate limits, works with school
  // accounts); the magic link stays available but starts collapsed.
  const [showEmail, setShowEmail] = useState(false);

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
    <main className="bleed-root min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-5xl flex-col">
        <AppNav
          right={
            <Link
              href="/"
              className="text-sm font-semibold text-aurora"
            >
              Back home
            </Link>
          }
        />

        <section className="grid flex-1 items-center gap-10 py-12 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="eyebrow">Student sign in</p>
            {gated ? (
              <p className="mt-4 max-w-xl border-l-2 border-star pl-4 text-sm leading-6 text-foreground">
                {from ? (
                  <>
                    <span className="font-mono text-xs text-muted-foreground">
                      {from}
                    </span>{" "}
                    is built from your own assessment, so it needs an account.
                  </>
                ) : (
                  "That page is built from your own assessment, so it needs an account."
                )}{" "}
                <Link href="/opportunities" className="underline">
                  The opportunity shelf
                </Link>{" "}
                is open to everyone without one.
              </p>
            ) : null}
            <h1 className="h-display mt-4 text-title text-foreground">
              Start with Northstar.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-8 text-muted-foreground">
              Sign in to save your trait profile and get opportunities ranked
              against it — plus bookmarks, logged outcomes, and a shareable
              record of what you have done.
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
            <p className="mt-2 text-center text-xs leading-5 text-muted-foreground">
              Fastest option — school Google accounts work. New here? Signing
              in creates your account.
            </p>

            {!showEmail ? (
              <button
                type="button"
                onClick={() => setShowEmail(true)}
                className="mt-6 w-full text-center text-sm text-muted-foreground underline underline-offset-4 transition hover:text-foreground"
              >
                Prefer email? Send yourself a sign-in link
              </button>
            ) : (
              <>
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
                    autoFocus
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
              </>
            )}

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

/**
 * useSearchParams needs a Suspense boundary, or the whole route opts out of
 * static rendering at build time.
 */
export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginInner />
    </Suspense>
  );
}
