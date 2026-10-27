"use client";

/**
 * RoadmapTree, the plan as a branching route, roadmap.sh style.
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
 *   dashed magenta  our generalisation, the same --advisory overprint the step
 *                   cards use for an authored edge_note, so the two agree
 *   dotted grey     nothing gates it; it belongs to that stage, that is all
 *
 * ACCESSIBILITY. The nodes are one <ol> in ladder order with real text, so the
 * sequence survives without the picture; the SVG carries only the connectors and
 * is hidden. Every node is an anchor to its own card in the list below, which
 * means it works with no JavaScript, keyboard-navigates in ladder order, and
 * gives a screen reader "link, Apply to RSI" rather than an unlabelled dot.
 *
 * Coordinates: x is a percentage, y is pixels. The SVG scales non-uniformly to
 * match, which is why every stroke is non-scaling and every connector is a
 * right-angle elbow, an axis-aligned line cannot be skewed by that scale.
 */

import { useEffect, useRef, useState } from "react";
import { FieldPlanet } from "@/components/decor/field-planets";
import { Ship } from "@/components/decor/voyage";
import { BRANCH_MAX_DEPTH } from "@/components/SubSteps";
import { fieldColor } from "@/lib/field-colors";
import type { EdgeKind, NodeKind, RoadmapTree as Tree, TreeNode } from "@/lib/roadmap-graph";
import type { OpportunityField } from "@/lib/types";

/**
 * Row pitch, in pixels.
 *
 * A node is a chip (~16px), 1-3 clamped title lines (20px each on the trunk)
 * and 8px of padding top and bottom: about 100px at its tallest. 132 leaves a
 * real gap between a full-height node and the next row instead of the 18px
 * that made two neighbouring cards read as one box.
 */
// 132 before the nodes carried a "+ steps" hint. That line is ~19px, which
// put a three-line trunk title at ~117px inside a 132px row: no overlap, but
// 7px of clearance, and the last time a node outgrew its row LEARN and BUILD
// drew as one merged box. Headroom is cheaper than that bug.
const ROW_H = 146;
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

type BreakDown = {
  /** null when this node cannot be broken down: root, horizon, or at the cap. */
  onBreak: (() => void) | null;
  busy: boolean;
  hasBranches: boolean;
  kind: "step" | "mission";
  selected: boolean;
};

function Node({
  node,
  here,
  breakdown,
}: {
  node: TreeNode;
  here: boolean;
  breakdown: BreakDown;
}) {
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
        <span
          className={`font-mono text-[0.6rem] uppercase tracking-[0.16em] ${
            node.nodeKind === "horizon" ? "text-polaris" : "text-aurora"
          }`}
        >
          {node.badge ?? KIND_LABEL[node.nodeKind]}
        </span>
      </span>
      <span
        /* NO `block` HERE. line-clamp-3 works by setting display:-webkit-box,
           and `block` sets display:block, whichever Tailwind emits later
           wins, which was `block`. So the clamp never applied, a long step
           title rendered all ten of its lines, and the node overflowed its
           118px row into the one below it. That is the overlap on /plan:
           LEARN and BUILD drawn as one merged box. */
        className={`mt-1 ${
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
      {/* CLICK THE NODE.
          The branches already draw on this diagram, so the diagram is where a
          student expects to open one. Before this the only way in was a
          control in the text list below, past the fold, and the author of the
          feature could not find it on his own page.

          A button, not a link to the anchor: the anchor scrolled away from
          the thing just clicked. Nodes that cannot be broken down (the root,
          the horizon markers, anything at the depth cap) fall back to the
          anchor so the diagram stays navigable. */}
      {breakdown.onBreak ? (
        <button
          type="button"
          onClick={breakdown.onBreak}
          disabled={breakdown.busy}
          aria-label={
            breakdown.kind === "mission"
              ? `Open mission: ${node.title}`
              : breakdown.hasBranches
                ? `Rewrite the steps inside: ${node.title}`
                : `Break into steps: ${node.title}`
          }
          aria-pressed={breakdown.kind === "mission" ? breakdown.selected : undefined}
          title={node.title}
          className={`${shell} w-full ${
            breakdown.busy ? "animate-pulse border-star" : "hover:border-star"
          } ${breakdown.selected ? "border-star bg-star/10" : ""}`}
        >
          {body}
          <span className="mt-1.5 block font-mono text-[0.55rem] uppercase tracking-[0.14em] text-aurora">
            {breakdown.kind === "mission"
              ? breakdown.selected
                ? "open"
                : "read it"
              : breakdown.busy
                ? "breaking down…"
                : breakdown.hasBranches
                  ? "+ again"
                  : "+ steps"}
          </span>
        </button>
      ) : node.step ? (
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
  onBreakDown,
  branching = null,
  branches = {},
  onSelectMission,
  selectedKey = null,
}: {
  tree: Tree;
  hereKey?: string | null;
  className?: string;
  /** Omit and the diagram is read-only, which is what signed-out callers want. */
  onBreakDown?: (step: {
    step_key: string;
    title: string;
    category: string;
  }) => void;
  branching?: string | null;
  branches?: Record<string, unknown[]>;
  /** A mission opens a panel instead of breaking down: it is already written. */
  onSelectMission?: (node: TreeNode) => void;
  selectedKey?: string | null;
}) {
  /**
   * Centre the canvas on the trunk once it exists.
   *
   * At 390px the canvas is twice the viewport, and a scroller starts at
   * scrollLeft 0, so a student on a phone opened this to the left-hand
   * branches with the trunk entirely off-screen, which is the one part they
   * need. Does nothing on a wide screen, where there is no overflow to centre.
   */
  const scroller = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = scroller.current;
    if (!node) return;
    node.scrollLeft = Math.max(0, (node.scrollWidth - node.clientWidth) / 2);
  }, [tree]);

  /**
   * Zoom, and drag to move around.
   *
   * A plan with three applications and a few breakdowns is wider and taller
   * than a laptop viewport, and a horizontal scrollbar is a poor way to read
   * a diagram. Zoom is a transform on the canvas rather than a change to the
   * layout maths, so every node keeps its position relative to its edges and
   * nothing re-flows at a new scale.
   *
   * Deliberately NOT bare-wheel zoom: the diagram sits in a long page, and
   * hijacking the wheel traps a reader trying to scroll past it. Ctrl or the
   * meta key with the wheel is the gesture browsers already use for zoom, and
   * the buttons work for everyone else.
   */
  const [zoom, setZoom] = useState(1);
  const nudge = (by: number) =>
    setZoom((z) => Math.min(1.8, Math.max(0.5, Math.round((z + by) * 20) / 20)));

  const drag = useRef<{ x: number; y: number; left: number; top: number } | null>(
    null,
  );
  const [dragging, setDragging] = useState(false);

  function onPointerDown(event: React.PointerEvent<HTMLDivElement>) {
    // Only a drag on empty canvas. A pointerdown that started on a node is
    // that node's click, and stealing it would make the diagram unusable.
    if ((event.target as HTMLElement).closest("button, a")) return;
    const node = scroller.current;
    if (!node) return;
    drag.current = {
      x: event.clientX,
      y: event.clientY,
      left: node.scrollLeft,
      top: node.scrollTop,
    };
    setDragging(true);
    node.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event: React.PointerEvent<HTMLDivElement>) {
    const start = drag.current;
    const node = scroller.current;
    if (!start || !node) return;
    node.scrollLeft = start.left - (event.clientX - start.x);
    node.scrollTop = start.top - (event.clientY - start.y);
  }

  function endDrag(event: React.PointerEvent<HTMLDivElement>) {
    if (!drag.current) return;
    drag.current = null;
    setDragging(false);
    scroller.current?.releasePointerCapture(event.pointerId);
  }

  function onWheel(event: React.WheelEvent<HTMLDivElement>) {
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    nudge(event.deltaY > 0 ? -0.1 : 0.1);
  }

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
      {/* Sideways scroll rather than a reflow. The columns ARE the data, one
          column is one programme, its gate stacked above it, and letting them
          wrap on a narrow screen would put a gate above a different programme's
          application, which is worse than a scrollbar. */}
      <div className="mt-3 flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => nudge(-0.1)}
          disabled={zoom <= 0.5}
          aria-label="Zoom out"
          className="border border-border px-2 py-1 font-mono text-xs text-muted-foreground transition hover:border-foreground hover:text-foreground disabled:opacity-40"
        >
          &minus;
        </button>
        <button
          type="button"
          onClick={() => nudge(0.1)}
          disabled={zoom >= 1.8}
          aria-label="Zoom in"
          className="border border-border px-2 py-1 font-mono text-xs text-muted-foreground transition hover:border-foreground hover:text-foreground disabled:opacity-40"
        >
          +
        </button>
        <button
          type="button"
          onClick={() => {
            setZoom(1);
            const node = scroller.current;
            if (node) {
              node.scrollLeft = Math.max(0, (node.scrollWidth - node.clientWidth) / 2);
              node.scrollTop = 0;
            }
          }}
          className="border border-border px-2 py-1 text-xs text-muted-foreground transition hover:border-foreground hover:text-foreground"
        >
          Reset
        </button>
        <span className="ml-1 font-mono text-[0.65rem] text-muted-foreground">
          {Math.round(zoom * 100)}% &middot; drag to move
        </span>
      </div>
      <div
        ref={scroller}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onWheel={onWheel}
        className={`overflow-auto overscroll-contain pb-2 ${
          dragging ? "cursor-grabbing select-none" : "cursor-grab"
        }`}
        style={{ maxHeight: "min(70vh, 720px)" }}
      >
        <div
          className="relative origin-top-left"
          style={{
            minWidth: MIN_W,
            height,
            transform: `scale(${zoom})`,
            width: `${100 / zoom}%`,
          }}
        >
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
            {tree.nodes.map((node) => {
              // Mirrors SubSteps: the root and the horizon markers are not
              // steps, and nothing past the cap may be opened. Counting
              // "::branch:" is the same depth rule the server enforces.
              const depth = node.key.split("::branch:").length - 1;
              // A mission is written by hand and already has its text; there
              // is nothing for a model to break down, so clicking it opens it.
              const isMission = node.nodeKind === "mission";
              const openable =
                !isMission &&
                Boolean(onBreakDown) &&
                node.nodeKind !== "root" &&
                node.nodeKind !== "horizon" &&
                depth < BRANCH_MAX_DEPTH;
              return (
                <Node
                  key={node.key}
                  node={node}
                  here={node.key === hereKey}
                  breakdown={{
                    onBreak: isMission
                      ? onSelectMission
                        ? () => onSelectMission(node)
                        : null
                      : openable && onBreakDown
                        ? () =>
                            onBreakDown({
                              step_key: node.key,
                              title: node.title,
                              category: node.step?.category ?? "step",
                            })
                        : null,
                    busy: branching === node.key,
                    hasBranches: Boolean(branches[node.key]),
                    kind: isMission ? "mission" : "step",
                    selected: selectedKey === node.key,
                  }}
                />
              );
            })}
          </ol>
        </div>
      </div>

      <figcaption className="mt-3 grid gap-2 text-xs leading-5 text-muted-foreground sm:grid-cols-3">
        <span className="flex items-start gap-2">
          <Rule kind="required" />
          <span>
            <span className="text-foreground">Required.</span> The programme&rsquo;s own
            entry rule.
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
        {/* Said once, here, rather than left as an unexplained orphan row: a
            node with no edge into it looks like a drawing error until you know
            that nothing on this tree reaches it.

            Only when there IS one. A legend entry explaining a mark that does
            not appear on the figure is a different kind of confusion: the
            reader goes looking for it. */}
        <span
          className={`flex items-start gap-2 sm:col-span-3 ${
            tree.nodes.some((n) => n.nodeKind === "horizon") ? "" : "hidden"
          }`}
        >
          <span
            aria-hidden="true"
            className="mt-1 h-3 w-7 shrink-0 rounded-sm border border-dashed border-border"
          />
          <span>
            <span className="text-foreground">No line into it.</span> A locked
            programme, drawn with no edge because no step on this tree reaches
            it. Only a birthday does, and the grade it opens at is on the node.
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
