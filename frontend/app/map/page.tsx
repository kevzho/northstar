"use client";

/**
 * Northstar pathway map — D3 force-directed graph.
 *
 * Nodes are the student's top matched opportunities (sized by score,
 * colored by field). Edges connect opportunities that share a field or
 * tags. The graph is fetched from GET /pathways on mount and rendered
 * into an SVG via d3-force.
 *
 * Per ARCHITECTURE.md, the node-edge model is a major technical
 * differentiator. This page is the judge-facing centerpiece.
 */

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { useRouter } from "next/navigation";
import * as d3 from "d3";

type GraphNode = {
  id: string;
  title: string;
  field: string;
  type: string;
  score: number;
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
};

export default function MapPage() {
  const router = useRouter();
  const svgRef = useRef<SVGSVGElement>(null);
  const [data, setData] = useState<GraphData>(null);
  const [loading, setLoading] = useState(true);

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
    if (!data || !svgRef.current || data.nodes.length === 0) return;

    const width = 800;
    const height = 600;

    // Clear previous render
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3
      .select(svgRef.current)
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("preserveAspectRatio", "xMidYMid meet")
      .style("width", "100%")
      .style("height", "auto")
      // Let the zoom/drag handlers own the gestures instead of the page
      // scroller, so pinch-zoom on the graph does not scroll the phone.
      .style("touch-action", "none");

    // Everything renders inside this group so zoom/pan is a single transform.
    const viewport = svg.append("g");

    // Build link/target refs for d3-force
    const nodes = data.nodes.map((n) => ({ ...n }));
    const links = data.edges.map((e) => ({
      source: e.source,
      target: e.target,
      weight: e.weight,
    }));

    const sim = d3
      .forceSimulation(nodes as d3.SimulationNodeDatum[])
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(80))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = viewport
      .append("g")
      .selectAll("line")
      .data(links)
      .enter()
      .append("line")
      .attr("stroke", "#3f3f3f")
      .attr("stroke-width", (d) => Math.max(1, d.weight * 4))
      .attr("stroke-opacity", 0.7);

    const node = viewport
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .enter()
      .append("circle")
      .attr("r", (d) => 8 + (d as GraphNode).score * 20)
      .attr("fill", (d) => fieldColors[(d as GraphNode).field] ?? "#9e9e9e")
      .attr("stroke", "#0a0a0a")
      .attr("stroke-width", 1.5)
      .style("cursor", "pointer");

    const labels = viewport
      .append("g")
      .selectAll("text")
      .data(nodes)
      .enter()
      .append("text")
      .text((d) => (d as GraphNode).title.slice(0, 20))
      .attr("font-size", 10)
      .attr("fill", "#d4d4d4")
      .attr("dx", 12)
      .attr("dy", 4)
      .style("pointer-events", "none");

    // Tooltip via title
    node.append("title").text(
      (d) =>
        `${(d as GraphNode).title}\nScore: ${Math.round((d as GraphNode).score * 100)}%\nField: ${(d as GraphNode).field}`,
    );

    /* eslint-disable @typescript-eslint/no-explicit-any */

    // Pinch/scroll to zoom, drag the background to pan. The viewBox is a fixed
    // 800x600, so on a phone the graph is scaled down to ~40% and labels are
    // unreadable without this.
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.4, 4])
      .on("zoom", (event) => viewport.attr("transform", event.transform));
    svg.call(zoom as any);

    // Drag individual nodes. `dragged` distinguishes a drag from a tap so
    // repositioning a node does not also navigate away from the map.
    let dragged = false;
    node.call(
      d3
        .drag<SVGCircleElement, any>()
        .on("start", (event, d) => {
          dragged = false;
          if (!event.active) sim.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          dragged = true;
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) sim.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }) as any,
    );

    node.on("click", (_event, d) => {
      if (dragged) return;
      router.push(`/opportunities/${(d as GraphNode).id}`);
    });

    sim.on("tick", () => {
      link
        .attr("x1", (d: any) => (d.source as unknown as { x: number }).x)
        .attr("y1", (d: any) => (d.source as unknown as { y: number }).y)
        .attr("x2", (d: any) => (d.target as unknown as { x: number }).x)
        .attr("y2", (d: any) => (d.target as unknown as { y: number }).y);
      node
        .attr("cx", (d: unknown) => (d as { x: number }).x)
        .attr("cy", (d: unknown) => (d as { y: number }).y);
      labels
        .attr("x", (d: unknown) => (d as { x: number }).x)
        .attr("y", (d: unknown) => (d as { y: number }).y);
    });
    /* eslint-enable @typescript-eslint/no-explicit-any */

    return () => {
      sim.stop();
    };
  }, [data, router]);

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="flex items-center justify-between border-b border-border pb-5">
          <Link
            href="/dashboard"
            className="h-display text-xl text-foreground"
          >
            Northstar
          </Link>
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="text-sm font-semibold text-aurora"
            >
              Back to dashboard
            </Link>
            <ThemeToggle />
          </div>
        </div>

        <header className="mt-10">
          <p className="eyebrow">Pathway map</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            Your night sky
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
            Each node is an opportunity matched to your profile. Edges connect
            programs that share a field or tags — your pathway through STEM.
            Click any node to see details.
          </p>
        </header>

        {/* Legend */}
        <section className="mt-6 flex flex-wrap gap-3">
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
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <p className="font-mono text-sm text-muted-foreground">
              Building your pathway map...
            </p>
          </section>
        ) : !data || data.nodes.length === 0 ? (
          <section className="rounded-lg border bg-card mt-10 p-8 text-center">
            <h2 className="text-xl font-semibold text-foreground">
              No map yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Complete onboarding and run the seed data to populate your
              pathway graph.
            </p>
            <Button render={<Link href="/onboarding" />} className="mt-6 h-11 px-5 font-semibold">
              Go to onboarding
            </Button>
          </section>
        ) : (
          <section className="rounded-lg border bg-card mt-8 p-4">
            <svg ref={svgRef} className="block w-full" />
            <p className="mt-3 text-xs leading-5 text-muted-foreground">
              Scroll or pinch to zoom, drag the background to pan, drag a node to
              reposition it. Tap a node to open the opportunity.
            </p>
          </section>
        )}
      </div>
    </main>
  );
}
