import type { MetadataRoute } from "next";

/**
 * Keep public student records out of search indexes.
 *
 * /p/<handle> is deliberately unauthenticated — it is the record a student
 * pastes into an application — but "shareable with a link" is not the same
 * as "indexed forever." These pages belong to minors: a first name, six
 * behavioral trait scores, a field-interest map, chosen path, social links
 * and logged outcomes. A student who clears their handle expects the page
 * to go with it, which cannot happen once a crawler has cached it.
 *
 * Disallowed alongside it: the signed-in app surface, which renders nothing
 * without a session anyway and only wastes crawl budget, and /auth, which
 * carries tokens in the URL fragment.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/p/", "/auth/", "/dashboard", "/profile", "/friends", "/discover", "/teamup"],
    },
  };
}
