import type { MetadataRoute } from "next";

/**
 * Keep public student records, and the signed-in surface, out of search.
 *
 * /p/<handle> is deliberately unauthenticated — it is the record a student
 * pastes into an application — but "shareable with a link" is not the same
 * as "indexed forever." These pages belong to minors: a first name, six
 * behavioral trait scores, a field-interest map, chosen path, social links
 * and logged outcomes. A student who clears their handle expects the page
 * to go with it, which cannot happen once a crawler has cached it. That
 * subtree also sends a real `noindex` header (app/p/[handle]/layout.tsx),
 * because robots.txt only reaches crawlers that ask for it first.
 *
 * Everything else below needs a session and renders nothing without one, so
 * indexing it only spends crawl budget on empty pages. This list is the
 * whole authenticated surface — it previously named five of fourteen while
 * the comment claimed to cover them all.
 *
 * Deliberately crawlable: /, /login, /faq, /contact, /privacy, and
 * /assessment — the assessment runs anonymously and is the better funnel.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/p/",
        "/auth/",
        "/advisor",
        "/dashboard",
        "/discover",
        "/friends",
        "/futures",
        "/map",
        "/mentors",
        "/onboarding",
        "/opportunities",
        "/plan",
        "/profile",
        "/projects",
        "/teamup",
      ],
    },
  };
}
