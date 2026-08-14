"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
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
      <div className="rounded-lg border bg-card w-full max-w-md p-6 text-center">
        <p className="eyebrow">Northstar</p>
        <h1 className="h-display mt-3 text-3xl text-foreground">
          Signing you in
        </h1>
        <p className="mt-4 text-sm leading-6 text-muted-foreground">{message}</p>
        <Button variant="outline" render={<Link href="/login" />} className="mt-6 h-11 px-5 font-semibold">
          Back to login
        </Button>
      </div>
    </main>
  );
}
