/**
 * Next.js 16 Proxy (replaces middleware.ts).
 *
 * Redirects unauthenticated users away from protected routes to /login.
 * Protected routes: /dashboard, /opportunities, /profile, /plan, /futures.
 * Public routes (always allowed): /, /login, /auth/callback, /onboarding.
 *
 * Docs: node_modules/next/dist/docs/01-app/02-guides/authentication.md
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected =
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/opportunities") ||
    pathname.startsWith("/profile") ||
    pathname.startsWith("/plan") ||
    pathname.startsWith("/futures") ||
    pathname.startsWith("/map") ||
    pathname.startsWith("/mentors");

  if (!isProtected) {
    return NextResponse.next();
  }

  // Check for auth cookie presence (optimistic; actual auth state is client-side).
  // This prevents even loading protected pages before JS boots.
  const hasSession = request.cookies.has("sb-access-token");
  if (!hasSession) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next|favicon.ico|public).*)"],
};
