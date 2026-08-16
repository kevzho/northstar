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
import { AppNav } from "@/components/AppNav";
import { useRouter } from "next/navigation";
import * as d3 from "d3";

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

    /* Chronological tree: You -> field branches -> deadline-ordered
       chains. Depth reads as time; the deepest leaf is the furthest
       deadline. Static layout — no simulation, same picture every visit. */
    type TreeDatum = {
      kind: "root" | "field" | "opp";
      label: string;
      field?: string;
      node?: GraphNode;
      children?: TreeDatum[];
    };

    const byField = d3.group(data.nodes, (n) => n.field || "interdisciplinary");
    const fieldOrder = [...byField.entries()].sort(
      (a, b) =>
        (d3.max(b[1], (n) => n.score) ?? 0) - (d3.max(a[1], (n) => n.score) ?? 0),
    );
    const branches: TreeDatum[] = fieldOrder.map(([field, nodes]) => {
      const ordered = [...nodes].sort((a, b) => {
        if (!a.deadline && !b.deadline) return b.score - a.score;
        if (!a.deadline) return 1;
        if (!b.deadline) return -1;
        return a.deadline < b.deadline ? -1 : 1;
      });
      let chain: TreeDatum | undefined;
      for (let i = ordered.length - 1; i >= 0; i -= 1) {
        chain = {
          kind: "opp",
          label: ordered[i].title,
          field,
          node: ordered[i],
          children: chain ? [chain] : undefined,
        };
      }
      return { kind: "field", label: field, field, children: chain ? [chain] : undefined };
    });

    const root = d3.hierarchy<TreeDatum>({
      kind: "root",
      label: "You",
      children: branches,
    });
    d3.tree<TreeDatum>().nodeSize([46, 210])(root);

    let xMin = Infinity;
    let xMax = -Infinity;
    let yMax = -Infinity;
    root.each((d) => {
      xMin = Math.min(xMin, d.x ?? 0);
      xMax = Math.max(xMax, d.x ?? 0);
      yMax = Math.max(yMax, d.y ?? 0);
    });
    const margin = 60;
    const width = yMax + 330;
    const height = xMax - xMin + margin * 2;

    d3.select(svgRef.current).selectAll("*").remove();
    const svg = d3
      .select(svgRef.current)
      .attr("viewBox", `-50 ${xMin - margin} ${width + 50} ${height}`)
      .attr("preserveAspectRatio", "xMidYMid meet")
      .style("width", "100%")
      .style("height", "auto")
      .style("touch-action", "none");

    const viewport = svg.append("g");

    // Links: gentle horizontal curves along the time axis.
    viewport
      .append("g")
      .selectAll("path")
      .data(root.links())
      .enter()
      .append("path")
      .attr("fill", "none")
      .attr("stroke", "#3f3f3f")
      .attr("stroke-width", 1.2)
      .attr("stroke-opacity", 0.6)
      .attr(
        "d",
        d3
          .linkHorizontal<d3.HierarchyLink<TreeDatum>, d3.HierarchyNode<TreeDatum>>()
          .x((d) => d.y ?? 0)
          .y((d) => d.x ?? 0),
      );

    const node = viewport
      .append("g")
      .selectAll("g")
      .data(root.descendants())
      .enter()
      .append("g")
      .attr("transform", (d) => `translate(${d.y ?? 0},${d.x ?? 0})`);

    node
      .append("circle")
      .attr("r", (d) =>
        d.data.kind === "root"
          ? 10
          : d.data.kind === "field"
            ? 6
            : 5 + (d.data.node?.score ?? 0) * 12,
      )
      .attr("fill", (d) =>
        d.data.kind === "root"
          ? "#f5f5f5"
          : fieldColors[d.data.field ?? ""] ?? "#9e9e9e",
      )
      .attr("fill-opacity", (d) => (d.data.kind === "field" ? 0.45 : 1))
      .attr("stroke", "#0a0a0a")
      .attr("stroke-width", 1.5)
      .style("cursor", (d) => (d.data.kind === "opp" ? "pointer" : "default"));

    node
      .append("text")
      .text((d) =>
        d.data.kind === "opp" ? d.data.label.slice(0, 28) : d.data.label,
      )
      .attr("font-size", (d) => (d.data.kind === "root" ? 12 : 10))
      .attr("font-weight", (d) => (d.data.kind === "opp" ? 400 : 600))
      .attr("fill", "#d4d4d4")
      .attr("dx", (d) => (d.data.kind === "root" ? -14 : 12))
      .attr("dy", (d) => (d.data.kind === "root" ? 24 : -8))
      .attr("text-anchor", (d) => (d.data.kind === "root" ? "middle" : "start"))
      .style("text-transform", (d) => (d.data.kind === "field" ? "capitalize" : "none"))
      .style("pointer-events", "none");

    // Deadline under each opportunity: the chronology made legible.
    node
      .filter((d) => d.data.kind === "opp")
      .append("text")
      .text((d) => d.data.node?.deadline ?? "rolling")
      .attr("font-size", 9)
      .attr("font-family", "var(--font-coords), monospace")
      .attr("fill", "#8a8a8a")
      .attr("dx", 12)
      .attr("dy", 6)
      .style("pointer-events", "none");

    node
      .filter((d) => d.data.kind === "opp")
      .append("title")
      .text(
        (d) =>
          `${d.data.node?.title}\nScore: ${Math.round((d.data.node?.score ?? 0) * 100)}%\nDeadline: ${d.data.node?.deadline ?? "rolling"}`,
      );

    node.on("click", (_event, d) => {
      if (d.data.kind === "opp" && d.data.node) {
        router.push(`/opportunities/${d.data.node.id}`);
      }
    });

    /* eslint-disable @typescript-eslint/no-explicit-any */
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.4, 4])
      .on("zoom", (event) => viewport.attr("transform", event.transform));
    svg.call(zoom as any);
    /* eslint-enable @typescript-eslint/no-explicit-any */
  }, [data, router]);

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
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
          <h1 className="h-display mt-3 text-4xl text-foreground">
            Your night sky
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
            Time flows left to right: each branch is a field, each step the
            next deadline on that path. The deepest leaves are your furthest
            horizons. Click any opportunity to see details.
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
