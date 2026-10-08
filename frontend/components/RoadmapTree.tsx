"use client";

/**
 * RoadmapTree — the plan as a branching route, roadmap.sh style.
 *
 * Replaces JourneyMap, which drew one horizontal row of dots per phase. That
 * said WHEN but could not say WHICH THING UNLOCKS WHICH, and the second is the
 * question a student actually has. lib/roadmap-graph.ts derives the structure;
 * this file is only its drawing.
 *
 * THE LEGEND IS LOAD-BEARING. An arrow reads as "you must", so the three edge
 * kinds are drawn differently and named in the key underneath:
 *
 *   solid gold      the programme's own rule (entry_gate / entry_note)
 *   dashed magenta  our generalisation — the same --advisory overprint the step
 *                   cards use for an authored edge_note, so the two agree
 *   dotted grey     nothing gates it; it belongs to that stage, that is all
 *
 * ACCESSIBILITY. The nodes are one <ol> in ladder order with real text, so the
 * sequence survives without the picture; the SVG carries only the connectors and
 * is hidden. Every node is an anchor to its own card in the list below — which
 * means it works with no JavaScript, keyboard-navigates in ladder order, and
 * gives a screen reader "link, Apply to RSI" rather than an unlabelled dot.
 *
 * Coordinates: x is a percentage, y is pixels. The SVG scales non-uniformly to
 * match, which is why every stroke is non-scaling and every connector is a
 * right-angle elbow — an axis-aligned line cannot be skewed by that scale.
 */

import { FieldPlanet } from "@/components/decor/field-planets";
import { Ship } from "@/components/decor/voyage";
import { fieldColor } from "@/lib/field-colors";
import type { EdgeKind, NodeKind, RoadmapTree as Tree, TreeNode } from "@/lib/roadmap-graph";
import type { OpportunityField } from "@/lib/types";

const ROW_H = 118;
/** Canvas floor. Four canopy columns need this much room before they collide. */
const MIN_W = "46rem";

const EDGE_STYLE: Record<EdgeKind, { stroke: string; width: number; dash?: string }> = {
  required: { stroke: "var(--polaris)", width: 2 },
  common: { stroke: "var(--advisory)", width: 1.6, dash: "6 5" },
  anytime: { stroke: "var(--border-bright)", width: 1.2, dash: "1.5 5" },
};

/** What a student calls this kind of node. */
const KIND_LABEL: Record<NodeKind, string> = {
  root: "Start",
  learn: "Learn",
  build: "Build",
  publish: "Publish",
  gate: "Get in",
  apply: "Apply",
  mission: "Mission",
  outreach: "Reach out",
  step: "Do",
  horizon: "Locked",
};

/** The glyph when no field is known — drawn from the same planet set. */
const KIND_PLANET: Record<NodeKind, OpportunityField> = {
  root: "interdisciplinary",
  learn: "math",
  build: "engineering",
  publish: "design",
  gate: "physics",
  apply: "cs",
  mission: "engineering",
  outreach: "humanities",
  step: "interdisciplinary",
  horizon: "health",
};

function centreY(row: number): number {
  return row * ROW_H + ROW_H / 2;
}

/**
 * One connector, as a right-angle elbow.
 *
 * Children of the same parent on the same row share the horizontal run, so a
 * fan of applications reads as one bus out of the trunk rather than four
 * diagonals crossing each other.
 */
function elbow(parent: TreeNode, child: TreeNode): string {
  const from = centreY(parent.row);
  const to = centreY(child.row);
  if (parent.row === child.row) return `M ${parent.x} ${from} H ${child.x}`;
  if (Math.abs(parent.x - child.x) < 0.01) return `M ${parent.x} ${from} V ${to}`;
  const bus = from + (to - from) / 2;
  return `M ${parent.x} ${from} V ${bus} H ${child.x} V ${to}`;
}

function Node({ node, here }: { node: TreeNode; here: boolean }) {
  const trunk = node.weight === "trunk";
  const colour = node.field ? fieldColor(node.field) : undefined;
  const planet = (node.field as OpportunityField | null) ?? KIND_PLANET[node.nodeKind];
  const width = trunk ? 210 : 158;

  const body = (
    <>
      <span className="flex items-center gap-1.5">
        <FieldPlanet
          field={planet}
          className={trunk ? "h-4 w-4" : "h-3.5 w-3.5"}
          style={colour ? { color: colour } : undefined}
        />
        <span className="font-mono text-[0.6rem] uppercase tracking-[0.16em] text-aurora">
          {KIND_LABEL[node.nodeKind]}
        </span>
      </span>
      <span
        className={`mt-1 block ${
          trunk ? "text-[0.8rem] leading-5 text-foreground" : "text-xs leading-[1.15rem]"
        } ${node.nodeKind === "horizon" ? "text-muted-foreground" : ""} line-clamp-3`}
      >
        {node.title}
      </span>
    </>
  );

  const shell = [
    "block rounded-md border px-3 py-2 text-left transition-colors",
    node.nodeKind === "root"
      ? "border-star bg-star/10"
      : node.nodeKind === "horizon"
        ? "border-dashed border-border bg-transparent"
        : trunk
          ? "border-border-bright bg-panel-raised hover:border-star"
          : "border-border bg-panel hover:border-star",
  ].join(" ");

  return (
    <li
      className="absolute"
      style={{
        left: `${node.x}%`,
        top: `${centreY(node.row)}px`,
        width,
        transform: "translate(-50%, -50%)",
      }}
      aria-current={here ? "step" : undefined}
    >
      {here ? (
        /* Ship sets aria-hidden itself; "you are here" is aria-current above. */
        <Ship className="absolute -top-5 left-1/2 h-4 w-3 -translate-x-1/2 text-star" />
      ) : null}
      {node.step ? (
        <a href={`#step-${node.step.step_key}`} className={shell} title={node.title}>
          {body}
        </a>
      ) : (
        <span className={shell} title={node.title}>
          {body}
        </span>
      )}
    </li>
  );
}

export function RoadmapTree({
  tree,
  hereKey,
  className = "",
}: {
  tree: Tree;
  hereKey?: string | null;
  className?: string;
}) {
  if (tree.nodes.length <= 1) return null;
  const byKey = new Map(tree.nodes.map((node) => [node.key, node]));
  const height = tree.rows * ROW_H;

  const edges = tree.nodes
    .filter((node) => node.parent && node.edge && byKey.has(node.parent))
    .map((node) => ({
      key: node.key,
      kind: node.edge as EdgeKind,
      d: elbow(byKey.get(node.parent as string) as TreeNode, node),
    }));

  return (
    <figure className={className}>
      {/* Sideways scroll rather than a reflow. The columns ARE the data — one
          column is one programme, its gate stacked above it — and letting them
          wrap on a narrow screen would put a gate above a different programme's
          application, which is worse than a scrollbar. */}
      <div className="overflow-x-auto pb-2">
        <div className="relative" style={{ minWidth: MIN_W, height }}>
          <svg
            aria-hidden="true"
            className="absolute inset-0 h-full w-full"
            viewBox={`0 0 100 ${height}`}
            preserveAspectRatio="none"
          >
            {edges.map((edge) => {
              const style = EDGE_STYLE[edge.kind];
              return (
                <path
                  key={edge.key}
                  d={edge.d}
                  fill="none"
                  stroke={style.stroke}
                  strokeWidth={style.width}
                  strokeDasharray={style.dash}
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                />
              );
            })}
          </svg>
          <ol className="absolute inset-0 list-none">
            {tree.nodes.map((node) => (
              <Node key={node.key} node={node} here={node.key === hereKey} />
            ))}
          </ol>
        </div>
      </div>

      <figcaption className="mt-3 grid gap-2 text-xs leading-5 text-muted-foreground sm:grid-cols-3">
        <span className="flex items-start gap-2">
          <Rule kind="required" />
          <span>
            <span className="text-foreground">Required.</span> The programme says
            so — its own entry rule.
          </span>
        </span>
        <span className="flex items-start gap-2">
          <Rule kind="common" />
          <span>
            <span className="text-foreground">A common route.</span> How students
            usually get there. Not a rule.
          </span>
        </span>
        <span className="flex items-start gap-2">
          <Rule kind="anytime" />
          <span>
            <span className="text-foreground">Any time.</span> Nothing is
            stopping you starting this today.
          </span>
        </span>
      </figcaption>
    </figure>
  );
}

function Rule({ kind }: { kind: EdgeKind }) {
  const style = EDGE_STYLE[kind];
  return (
    <svg aria-hidden="true" className="mt-2 h-1 w-7 shrink-0" viewBox="0 0 28 2">
      <path
        d="M0 1 H28"
        stroke={style.stroke}
        strokeWidth={style.width}
        strokeDasharray={style.dash}
        strokeLinecap="round"
      />
    </svg>
  );
}
