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

const fieldColors: Record<string, string> = {
  cs: "#2563eb",
  biology: "#16a34a",
  math: "#9333ea",
  physics: "#ea580c",
  engineering: "#0891b2",
  interdisciplinary: "#ca8a04",
};

export default function MapPage() {
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
      .style("max-width", "100%")
      .style("height", "auto");

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

    const link = svg
      .append("g")
      .selectAll("line")
      .data(links)
      .enter()
      .append("line")
      .attr("stroke", "#cbd5e1")
      .attr("stroke-width", (d) => Math.max(1, d.weight * 4))
      .attr("stroke-opacity", 0.5);

    const node = svg
      .append("g")
      .selectAll("circle")
      .data(nodes)
      .enter()
      .append("circle")
      .attr("r", (d) => 8 + (d as GraphNode).score * 20)
      .attr("fill", (d) => fieldColors[(d as GraphNode).field] ?? "#64748b")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .style("cursor", "pointer");

    const labels = svg
      .append("g")
      .selectAll("text")
      .data(nodes)
      .enter()
      .append("text")
      .text((d) => (d as GraphNode).title.slice(0, 20))
      .attr("font-size", 10)
      .attr("fill", "#1e293b")
      .attr("dx", 12)
      .attr("dy", 4)
      .style("pointer-events", "none");

    // Tooltip via title
    node.append("title").text(
      (d) =>
        `${(d as GraphNode).title}\nScore: ${Math.round((d as GraphNode).score * 100)}%\nField: ${(d as GraphNode).field}`,
    );

    node.on("click", (_event, d) => {
      window.location.href = `/opportunities/${(d as GraphNode).id}`;
    });

    /* eslint-disable @typescript-eslint/no-explicit-any */
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
  }, [data]);

  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-5">
          <Link
            href="/dashboard"
            className="text-lg font-semibold tracking-tight text-[var(--northstar-dark)]"
          >
            Northstar
          </Link>
          <Link
            href="/dashboard"
            className="text-sm font-semibold text-[var(--northstar)]"
          >
            Back to dashboard
          </Link>
        </div>

        <header className="mt-10">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--amber)]">
            Pathway map
          </p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[var(--northstar-dark)]">
            Your Northstar map
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-[var(--muted)]">
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
              <span className="text-xs font-semibold capitalize text-[var(--muted)]">
                {field}
              </span>
            </div>
          ))}
        </section>

        {loading ? (
          <section className="mt-10 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-8 text-center shadow-sm">
            <p className="text-sm font-semibold text-[var(--muted)]">
              Building your pathway map...
            </p>
          </section>
        ) : !data || data.nodes.length === 0 ? (
          <section className="mt-10 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-8 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-[var(--northstar-dark)]">
              No map yet
            </h2>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              Complete onboarding and run the seed data to populate your
              pathway graph.
            </p>
            <Link
              href="/onboarding"
              className="mt-6 inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
            >
              Go to onboarding
            </Link>
          </section>
        ) : (
          <section className="mt-8 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-4 shadow-sm">
            <svg ref={svgRef} />
          </section>
        )}
      </div>
    </main>
  );
}
