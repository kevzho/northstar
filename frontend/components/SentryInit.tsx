"use client";

/**
 * Browser error tracking, armed only when NEXT_PUBLIC_SENTRY_DSN is set.
 * A silent no-op locally and in CI; in production a crashed page reports
 * itself instead of waiting to be discovered by a visitor.
 */

import { useEffect } from "react";

export function SentryInit() {
  useEffect(() => {
    const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
    if (!dsn) return;
    import("@sentry/browser").then((Sentry) => {
      Sentry.init({ dsn, tracesSampleRate: 0 });
    });
  }, []);
  return null;
}
