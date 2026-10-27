"use client";

/**
 * Send a signed-out visitor to sign in, and say why when they get there.
 *
 * WHAT THIS REPLACES. Nothing, which was the problem. Measured on 2026-10-05,
 * no page redirected: /plan, /discover, /map, /profile and the rest each
 * rendered their heading and then an empty shell, while the API answered 401 to
 * /match, /discover and /roadmap. A locked door tells you it is locked; this
 * told you nothing, and the difference between "gated" and "broken" is the one
 * a first-time visitor cannot make.
 *
 * NOT FOR THE CATALOG. /opportunities serves the public shelf signed out and
 * must never call this: the shelf is the reason to make an account, and hiding
 * it behind the account is the mistake this whole change is undoing. This is
 * for pages that are genuinely about one person, their plan, their matches,
 * their profile, their friends.
 *
 * It passes `reason` and NOT `next`. Returning someone to where they were going
 * needs the OAuth callback to carry it through the round trip, which it does not
 * do today, and a query parameter that silently does nothing is worse than an
 * absent one, because the next person reads it as working.
 */

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/use-auth";

export function useRequireAuth(): { ready: boolean } {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Waiting is not the same as absent. Redirecting while the session is still
    // resolving bounces people who ARE signed in, on every hard refresh.
    if (loading || user) return;
    router.replace(`/login?reason=account&from=${encodeURIComponent(pathname ?? "/")}`);
  }, [loading, user, pathname, router]);

  return { ready: Boolean(user) };
}
