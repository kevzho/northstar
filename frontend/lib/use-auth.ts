"use client";

/**
 * Lightweight auth hook that wraps Supabase getUser().
 *\n * Returns { user, loading } so UI can gate content without duplicating the
 * getUser() call in every page. Drop-in replacement for the inline session
 * fetch in dashboard/page.tsx et al.
 */

import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { supabase } from "./supabase";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchUser() {
      const { data } = await supabase.auth.getUser();
      if (!cancelled) {
        setUser(data.user);
        setLoading(false);
      }
    }

    fetchUser();

    return () => {
      cancelled = true;
    };
  }, []);

  return { user, loading };
}
