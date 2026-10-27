import type { Metadata } from "next";

/**
 * robots.txt is advisory and only reaches crawlers that ask for it first.
 * This sends `noindex, nofollow` as a real directive on every public
 * student record, including for a crawler that arrived from a pasted link
 * and never fetched /robots.txt.
 *
 * The page stays fully reachable by anyone holding the URL, that is the
 * point of the record. It just stops being permanently searchable, which
 * matters because these pages belong to minors and a student who clears
 * their handle expects the page to go with it.
 *
 * This layout exists only to carry the metadata: page.tsx is a client
 * component, so it cannot export it itself.
 */
export const metadata: Metadata = {
  robots: { index: false, follow: false, nocache: true },
};

export default function PublicProfileLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
