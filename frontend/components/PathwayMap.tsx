"use client";

/**
 * The pathway map, as a section rather than a page.
 *
 * Lifted out of app/map/page.tsx so /plan can carry both views of one plan:
 * the roadmap tree says what to do in what order, this says which programmes
 * are out there and how soon they close. They were two routes answering one
 * question, and a student had to know to go looking for the second.
 *
 * WHAT DELIBERATELY DID NOT CHANGE, because an inventory pass found each of
 * these would break quietly:
 *
 *   The /pathways fetch stays hand-rolled. It is NOT /match: the server
 *   re-scores and returns the top 14 with a flat `score`, and /match nests
 *   score and field differently and has no cap. Swapping the source would
 *   change which planets exist and every planet's diameter. Routing it
 *   through authedFetch would also throw on the 404 that the "No map yet"
 *   empty state exists to catch.
 *
 *   `data` stays in local state, so its identity is stable. /plan re-renders
 *   on five separate pieces of state; a derived prop would redraw the map and
 *   throw away the viewer's pan on each one.
 *
 *   `view` stays in the d3 dependency array even though the effect's first
 *   line returns when it is not "map". In list view the <svg> is not mounted,
 *   so the ref is null when data lands -- `view` changing is the only thing
 *   that draws the map after a list -> map toggle.
 *
 *   The localStorage key stays "pathway-view". Renaming it would silently
 *   reset the preference for everyone who already set one.
 *
 *   The fetch effect and the preference effect stay in the same component.
 *   react-hooks/set-state-in-effect is an error in this config and the
 *   preference effect only passes while the fetch effect is its neighbour.
 *
 * WHAT CHANGED, and why:
 *
 *   No <main>, no AppNav, no useRequireAuth, no <h1>. The host page owns all
 *   four. Two <main> elements is invalid, two sticky navs fight over z-40,
 *   and two useRequireAuth calls race two router.replace calls.
 *
 *   A bare wheel no longer zooms, and touch-action is pan-y. See the effect.
 *
 *   At most MAX_SYSTEMS solar systems are drawn. See the effect.
 */

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import * as d3 from "d3";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { FIELD_COLORS } from "@/lib/field-colors";
import { LoadingSection } from "@/components/decor/orbit-loader";
import { PathwayList } from "@/components/PathwayList";

/* One source of truth for field colour -- shared with the profile's field sky
   so biology is the same green in both places. See lib/field-colors.ts. */
const fieldColors = FIELD_COLORS as Record<string, string>;

/**
 * How many fields get a solar system.
 *
 * Not a style choice. The svg is a fixed-aspect viewBox rendered at
 * width:100%, so its height is decided by the column width and the row count
 * and no CSS max-height can shrink it -- it would only crop. Two rows keeps
 * the figure near square whatever the student's profile looks like.
 */
const MAX_SYSTEMS = 4;

type GraphNode = {
  id: string;
  title: string;
  field: string;
  type: string;
  score: number;
  deadline?: string | null;
  tags: string[];
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
};

type GraphEdge = {
  source: string | GraphNode;
  target: string | GraphNode;
  weight: number;
};

type GraphData = { nodes: GraphNode[]; edges: GraphEdge[] } | null;

export function PathwayMap() {
  // NOTE: no useRequireAuth here. The page that renders this owns the
  // gate; a second call races a second router.replace.
  const router = useRouter();
  const svgRef = useRef<SVGSVGElement>(null);
  const [data, setData] = useState<GraphData>(null);
  const [loading, setLoading] = useState(true);
  // The picture is the default because it is what the page is for, but the
  // choice is sticky: someone who needs the list needs it every time, and
  // making them re-toggle on every visit is its own barrier. Reads are wrapped
  // because storage throws in private windows rather than returning null.
  const [view, setView] = useState<"map" | "list">("map");
  useEffect(() => {
    try {
      if (localStorage.getItem("pathway-view") === "list") setView("list");
    } catch {
      /* no stored preference available; the default stands */
    }
  }, []);
  function chooseView(next: "map" | "list") {
    setView(next);
    try {
      localStorage.setItem("pathway-view", next);
    } catch {
      /* preference simply will not persist */
    }
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { supabase } = await import("@/lib/supabase");
        const { data: session } = await supabase.auth.getSession();
        const token = session.session?.access_token;
        const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
        const res = await fetch(`${apiUrl}/pathways`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error(String(res.status));
        const json: GraphData = await res.json();
        if (!cancelled) setData(json);
      } catch {
        if (!cancelled) setData(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (view !== "map") return;
    if (!data || !svgRef.current || data.nodes.length === 0) return;

    /* Solar systems: one per field the student matches. A central sun
       (the field) with opportunity-planets orbiting it — inner orbits are
       sooner deadlines, so the closest planets are the most urgent.
       Deterministic layout (no physics) so the map is the same each
       visit. Planet sprites: Kenney's planet pack, /public/planets. */

    const byField = d3.group(
      data.nodes,
      (n) => n.field || "interdisciplinary",
    );
    const allSystems = [...byField.entries()]
      .map(([field, nodes]) => ({ field, nodes }))
      .sort((a, b) => b.nodes.length - a.nodes.length);
    // BOUNDED BY CONSTRUCTION, because the height cannot be bounded by CSS.
    // The svg is a fixed-aspect viewBox at width:100%, so rendered height is
    // column-width x (rows*560)/(cols*620) -- min-h and max-h do not change
    // it. Ten fields would drop ~2800px of diagram between the roadmap tree
    // and the step list. Four systems is two rows, which is ~0.9 of the
    // column width whatever the profile. The remainder is named below the
    // figure rather than silently dropped.
    const systems = allSystems.slice(0, MAX_SYSTEMS);

    const cols = systems.length <= 1 ? 1 : 2;
    const rows = Math.ceil(systems.length / cols);
    const CELL_W = 620;
    const CELL_H = 560;
    const width = cols * CELL_W;
    const height = rows * CELL_H;

    d3.select(svgRef.current).selectAll("*").remove();
    const svg = d3
      .select(svgRef.current)
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("preserveAspectRatio", "xMidYMid meet")
      .style("width", "100%")
      .style("height", "auto")
      // pan-y, NOT none. On /map this svg was most of a short page so
      // swallowing touch was the point. Here it sits mid-scroll above the
      // step list: touch-action:none means a swipe up over the map moves
      // nothing and a student never reaches their steps.
      .style("touch-action", "pan-y");
    const viewport = svg.append("g");

    // Deadline -> orbit index (0 = innermost/soonest). Rolling deadlines
    // sit on the outermost orbit.
    function daysOut(deadline?: string | null): number {
      if (!deadline) return 9999;
      const t = new Date(`${deadline}T23:59:59`).getTime();
      if (Number.isNaN(t)) return 9999;
      return Math.max(0, (t - Date.now()) / 86_400_000);
    }

    systems.forEach((system, si) => {
      const cx = (si % cols) * CELL_W + CELL_W / 2;
      const cy = Math.floor(si / cols) * CELL_H + CELL_H / 2;
      const color = fieldColors[system.field] ?? "#9e9e9e";

      const planets = [...system.nodes]
        .sort((a, b) => daysOut(a.deadline) - daysOut(b.deadline))
        .slice(0, 8);
      const minR = 90;
      const maxR = 250;

      const cell = viewport.append("g");

      // Orbit rings.
      planets.forEach((_, i) => {
        const r = minR + (maxR - minR) * (planets.length === 1 ? 0 : i / (planets.length - 1));
        cell
          .append("circle")
          .attr("cx", cx)
          .attr("cy", cy)
          .attr("r", r)
          .attr("fill", "none")
          .attr("stroke", color)
          .attr("stroke-opacity", 0.14)
          .attr("stroke-width", 1);
      });

      // The sun: a glowing field core.
      const sunGrad = `sun-${si}`;
      const defs = cell.append("defs");
      const grad = defs
        .append("radialGradient")
        .attr("id", sunGrad);
      grad.append("stop").attr("offset", "0%").attr("stop-color", color).attr("stop-opacity", 1);
      grad.append("stop").attr("offset", "70%").attr("stop-color", color).attr("stop-opacity", 0.5);
      grad.append("stop").attr("offset", "100%").attr("stop-color", color).attr("stop-opacity", 0);

      cell
        .append("circle")
        .attr("cx", cx)
        .attr("cy", cy)
        .attr("r", 54)
        .attr("fill", `url(#${sunGrad})`);
      cell
        .append("circle")
        .attr("cx", cx)
        .attr("cy", cy)
        .attr("r", 22)
        .attr("fill", color);
      cell
        .append("text")
        .attr("x", cx)
        .attr("y", cy + 5)
        .attr("text-anchor", "middle")
        .attr("font-size", 13)
        .attr("font-weight", 700)
        .attr("fill", "#0a0a0a")
        .style("text-transform", "capitalize")
        .style("pointer-events", "none")
        .text(system.field.slice(0, 3));
      cell
        .append("text")
        .attr("x", cx)
        .attr("y", cy - 66)
        .attr("text-anchor", "middle")
        .attr("font-size", 15)
        .attr("font-weight", 600)
        .attr("fill", "#d4d4d4")
        .style("text-transform", "capitalize")
        .style("pointer-events", "none")
        .text(system.field);

      // Planets on their orbits. Angle is deterministic per index so the
      // system looks composed, not random.
      planets.forEach((planet, i) => {
        const r =
          minR + (maxR - minR) * (planets.length === 1 ? 0 : i / (planets.length - 1));
        const angle = (i * 2.399963) % (Math.PI * 2); // golden-angle spread
        const px = cx + Math.cos(angle) * r;
        const py = cy + Math.sin(angle) * r;
        const size = 34 + planet.score * 30;
        // Sprite chosen deterministically from the opportunity id.
        const hash = [...planet.id].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
        const sprite = `/planets/planet0${hash % 10}.png`;

        const g = cell
          .append("g")
          .attr("transform", `translate(${px},${py})`)
          .style("cursor", "pointer")
          .on("click", () => router.push(`/opportunities/${planet.id}`));

        g.append("image")
          .attr("href", sprite)
          .attr("x", -size / 2)
          .attr("y", -size / 2)
          .attr("width", size)
          .attr("height", size);

        g.append("title").text(
          `${planet.title}\nDeadline: ${planet.deadline ?? "rolling"}\nFit: ${Math.round(planet.score * 100)}%`,
        );

        g.append("text")
          .text(planet.title.slice(0, 22))
          .attr("y", size / 2 + 14)
          .attr("text-anchor", "middle")
          .attr("font-size", 10)
          .attr("fill", "#d4d4d4")
          .style("pointer-events", "none");
        g.append("text")
          .text(planet.deadline ?? "rolling")
          .attr("y", size / 2 + 27)
          .attr("text-anchor", "middle")
          .attr("font-size", 9)
          .attr("font-family", "var(--font-coords), monospace")
          .attr("fill", "#8a8a8a")
          .style("pointer-events", "none");
      });
    });

    /* eslint-disable @typescript-eslint/no-explicit-any */
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 3])
      // Drag still pans. A bare wheel does NOT zoom any more -- it scrolls the
      // page, because this map is no longer the whole page. Ctrl/Cmd+wheel is
      // the browser's own zoom gesture and is what the caption now tells you
      // to use.
      .filter((event: any) => {
        // Wheel: only with ctrl/cmd, so a plain scroll moves the page.
        if (event.type === "wheel") return event.ctrlKey || event.metaKey;
        // Touch: TWO fingers or nothing. touch-action: pan-y is not enough on
        // its own -- once d3-zoom engages a touch gesture it sets __zooming
        // and calls noevent() on every touchmove, so a one-finger swipe over
        // the map is swallowed and the page does not scroll. Verified against
        // d3-zoom 3.0.0's own source. Leaving one finger to the browser is
        // what keeps a phone able to scroll past the figure.
        if (event.type.startsWith("touch")) {
          return event.touches && event.touches.length >= 2;
        }
        // Mouse drag still pans. The ctrl guard mirrors d3's own
        // defaultFilter, which treats ctrl+mousedown as a context-menu
        // gesture rather than a pan.
        return !event.ctrlKey && !event.button;
      })
      .on("zoom", (event) => viewport.attr("transform", event.transform));
    svg.call(zoom as any);
    /* eslint-enable @typescript-eslint/no-explicit-any */
  }, [data, router, view]);
  const hiddenFields =
    data && data.nodes.length
      ? [...new Set(data.nodes.map((n) => n.field || "interdisciplinary"))].length -
        MAX_SYSTEMS
      : 0;

  return (
    <div>
      {/* The toggle comes before the legend and the figure, so the first
          thing a keyboard user reaches is the control that gives them a view
          they can actually operate. */}
      <div
        role="group"
        aria-label="Choose how to view your matches"
        className="flex gap-2"
      >
        {([["map", "Map"], ["list", "List"]] as const).map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={view === value}
            onClick={() => chooseView(value)}
            className={
              view === value
                ? "border border-foreground bg-foreground px-4 py-2 text-sm font-medium text-background"
                : "border border-border bg-transparent px-4 py-2 text-sm font-medium text-foreground"
            }
          >
            {label}
            <span className="sr-only">
              {value === "list"
                ? " view: the same matches as a keyboard-navigable list"
                : " view: an orbital diagram, mouse and touch only"}
            </span>
          </button>
        ))}
      </div>

      <section aria-hidden={view === "list"} className="mt-4 flex flex-wrap gap-3">
        {Object.entries(fieldColors).map(([field, color]) => (
          <div key={field} className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-3 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="font-mono text-xs capitalize text-muted-foreground">
              {field}
            </span>
          </div>
        ))}
      </section>

      {loading ? (
        <LoadingSection label="Building your pathway map..." />
      ) : !data || data.nodes.length === 0 ? (
        <section className="mt-6 rounded-md border border-border bg-panel-raised p-6 text-center">
          <h3 className="h-display text-section text-foreground">No map yet</h3>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            The map is built from your ranked matches, so it fills in once you
            have finished onboarding and the assessment.
          </p>
          <Button render={<Link href="/onboarding" />} className="mt-5 h-10 px-4 font-semibold">
            Go to onboarding
          </Button>
        </section>
      ) : view === "map" ? (
        <>
          {/* Decorative by construction: every planet's meaning is in the
              list, so exposing the shapes would only hand a screen reader
              several hundred unlabelled nodes. */}
          {/* An opaque backing, scoped to the figure only.
              SpriteSky -- the fixed background on this page -- draws the SAME
              ten /planets/planet0*.png images this map uses for its
              data-bearing planets. Without a ground behind the svg, decorative
              sprites and real matched programmes are the same pictures at
              similar sizes, and the one thing the figure is for becomes
              ambiguous. The section's text stays backgroundless. */}
          <div
            aria-hidden="true"
            className="mt-4 rounded-md border border-border bg-panel/80 p-2"
          >
            <svg ref={svgRef} className="block w-full" />
          </div>
          <p className="sr-only">
            The map is a decorative diagram and cannot be operated by keyboard.
            Choose List view above for the same {data.nodes.length} matches as a
            navigable list.
          </p>
          <p className="mt-3 text-xs leading-5 text-muted-foreground">
            Drag to pan. Ctrl or cmd and scroll to zoom, or pinch with two
            fingers; a plain scroll or a one-finger swipe moves the page.
            Planet size is fit, the sun labels the field, and the innermost
            orbit closes soonest. Tap a planet to open it.
            {hiddenFields > 0 ? (
              <>
                {" "}
                {/* "most matches", not "strongest": the sort key is
                    nodes.length, and calling that strength would describe a
                    different ranking than the one on screen. */}
                Showing the {MAX_SYSTEMS} fields with the most matches;{" "}
                {hiddenFields} more{hiddenFields === 1 ? " field is" : " fields are"}{" "}
                in the list view, which has all of them.
              </>
            ) : null}
          </p>
        </>
      ) : (
        <PathwayList nodes={data.nodes} fieldColors={fieldColors} />
      )}
    </div>
  );
}
