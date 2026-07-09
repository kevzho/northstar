"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [message, setMessage] = useState("Completing sign in...");

  useEffect(() => {
    let isMounted = true;

    async function finishSignIn() {
      const { data, error } = await supabase.auth.getSession();

      if (!isMounted) {
        return;
      }

      if (error) {
        setMessage(error.message);
        return;
      }

      if (!data.session) {
        setMessage("No active session found. Try signing in again.");
        return;
      }

      router.replace("/dashboard");
    }

    finishSignIn();

    return () => {
      isMounted = false;
    };
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-8">
      <div className="w-full max-w-md rounded-lg border border-[var(--border)] bg-[var(--panel)] p-6 text-center shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--amber)]">
          Meridian
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-[var(--northstar-dark)]">
          Auth callback
        </h1>
        <p className="mt-4 text-sm leading-6 text-[var(--muted)]">{message}</p>
        <Link
          href="/login"
          className="mt-6 inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
        >
          Back to login
        </Link>
      </div>
    </main>
  );
}
