/**
 * /map is now /plan.
 *
 * The orbital diagram was its own route, which meant a student had to know to
 * go looking for the second half of their own plan -- and the dashboard tile
 * pointed here, at the picture, rather than at the instructions. The map is a
 * section of app/plan/page.tsx now, rendered by components/PathwayMap.tsx.
 *
 * This file stays as a redirect rather than being deleted, because the route
 * is in the nav aliases, in the demo script, and in anything a student has
 * bookmarked. Redirecting costs one file; breaking those costs trust in a
 * link.
 *
 * No hash on the target. There is no hash handling anywhere in this app, the
 * map section only exists after /pathways settles, and redirect() serves a
 * 307 the browser follows before the section is in the DOM -- so a #map
 * fragment would scroll nowhere and look broken.
 */

import { redirect } from "next/navigation";

export default function MapPage() {
  redirect("/plan");
}
