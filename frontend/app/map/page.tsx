"use client";

/**
 * Northstar pathway map — D3 orbital diagram.
 *
 * NOT a force-directed graph, despite what this comment used to say and
 * what the dashboard tile used to promise. Each FIELD is drawn as a star,
 * and the student's matched opportunities orbit the star for their field:
 * orbit index comes from the deadline (innermost closes soonest, rolling
 * deadlines sit outermost), angle is deterministic per index so the layout
 * is stable between renders. No edges are drawn between nodes.
 *
 * Data comes from GET /pathways, which returns nodes AND edges — the edges
 * are derived at request time from shared tags and field. This page uses
 * the nodes and ignores the edges.
 *
 * Accessibility: the SVG is decorative and mouse-only, so it is aria-hidden
 * and the page ships a conforming text alternative beside it — see
 * components/PathwayList.tsx, which carries the same data in the same order
 * with the same links. The view toggle is the first control after the nav, and
 * the choice is remembered, so a keyboard user does not re-make it every visit.
 */

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AppNav } from "@/components/AppNav";
import { useRouter } from "next/navigation";
import * as d3 from "d3";
import { LoadingSection } from "@/components/decor/orbit-loader";
import { PathwayList } from "@/components/PathwayList";
import { useRequireAuth } from "@/lib/use-require-auth";

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

/* Luminous star colors — tuned to read against the night-sky background. */
const fieldColors: Record<string, string> = {
  cs: "#6c9ef8",
  biology: "#56d394",
  math: "#c08bf5",
  physics: "#f09a62",
  engineering: "#55c7de",
  interdisciplinary: "#e7c868",
  design: "#f08bc9",
  business: "#a8d96c",
  humanities: "#dab07f",
  health: "#f07d7d",
};

export default function MapPage() {
  // Built from this student's own assessment, so it needs an account.
  // Signed out this used to render a heading and an empty shell while the
  // API answered 401 — gated and broken look identical from there.
  useRequireAuth();
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
    const systems = [...byField.entries()]
      .map(([field, nodes]) => ({ field, nodes }))
      .sort((a, b) => b.nodes.length - a.nodes.length);

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
      .style("touch-action", "none");
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
      .on("zoom", (event) => viewport.attr("transform", event.transform));
    svg.call(zoom as any);
    /* eslint-enable @typescript-eslint/no-explicit-any */
  }, [data, router, view]);

  return (
    <main className="min-h-screen px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-7xl">
        <AppNav
          homeHref="/dashboard"
          right={
            <Link
              href="/dashboard"
              className="text-sm font-semibold text-aurora"
            >
              Back to dashboard
            </Link>
          }
        />

        <header className="mt-10">
          <p className="eyebrow">Pathway map</p>
          <h1 className="h-display mt-3 text-title text-foreground">
            Your solar systems
          </h1>
          <p className="mt-4 max-w-2xl text-lede text-muted-foreground">
            Each field is a star; the opportunities matched to you orbit it.
            Inner orbits are the soonest deadlines — the closest planets are
            the most urgent. Open any of them to see the opportunity.
          </p>
        </header>

        {/* The toggle sits before the legend and the figure, so the first
            thing a keyboard user reaches is the control that gives them a
            view they can actually operate. */}
        <div
          role="group"
          aria-label="Choose how to view your pathways"
          className="mt-6 flex gap-2"
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

        {/* Legend */}
        <section aria-hidden={view === "list"} className="mt-6 flex flex-wrap gap-3">
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
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="h-display text-section text-foreground">
              No map yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Your map is built from your ranked matches, so it fills in once
              you have finished onboarding and the assessment.
            </p>
            <Button render={<Link href="/onboarding" />} className="mt-6 h-11 px-5 font-semibold">
              Go to onboarding
            </Button>
          </section>
        ) : (
          <section className="rounded-lg border bg-card mt-8 p-4">
            {view === "map" ? (
              <>
                {/* Decorative by construction: every planet's meaning is in
                    the list, so exposing the shapes would only hand a screen
                    reader several hundred unlabelled nodes. */}
                <div aria-hidden="true">
                  <svg ref={svgRef} className="block w-full min-h-[70vh]" />
                </div>
                <p className="sr-only">
                  The map is a decorative diagram and cannot be operated by
                  keyboard. Choose List view above for the same{" "}
                  {data.nodes.length} matches as a navigable list.
                </p>
                <p className="mt-3 text-xs leading-5 text-muted-foreground">
                  Scroll or pinch to zoom, drag the background to pan. Planet
                  size is fit; the sun labels the field. Tap a planet to open
                  the opportunity.
                </p>
              </>
            ) : (
              <PathwayList nodes={data.nodes} fieldColors={fieldColors} />
            )}
          </section>
        )}
      </div>
    </main>
  );
}
