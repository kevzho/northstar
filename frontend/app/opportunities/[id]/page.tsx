/**
 * Opportunity detail route.
 *
 * Next.js 16 convention: dynamic-route `params` is a Promise and must be awaited
 * (per node_modules/next/dist/docs/.../03-layouts-and-pages.md).
 *
 * The route stays a server component and only unwraps the id. All data fetching
 * happens in the client component below, because GET /opportunities/:id is
 * auth-gated and the Supabase access token only exists in the browser.
 */

import { OpportunityDetail } from "./OpportunityDetail";

export default async function Page(
  props: { params: Promise<{ id: string }> },
) {
  const { id } = await props.params;
  return <OpportunityDetail id={id} />;
}
