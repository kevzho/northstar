/**
 * The plan as a dependency tree.
 *
 * GET /roadmap returns a flat list of steps bucketed into phases by time, and
 * the page rendered it as exactly that: a vertical list of cards. A list can
 * say WHEN, but it cannot say WHICH THING UNLOCKS WHICH, and that is the whole
 * question a student has when they look at a plan. "Qualify for USAMO" sitting
 * two cards under "Start Khan Academy algebra" looks like two chores; drawn as
 * an edge it is a route.
 *
 * So this turns the flat list into a tree, roadmap.sh style: a trunk down the
 * middle for the work that compounds, branches to the sides for work that does
 * not depend on anything, and a canopy of applications at the top of the ladder
 * where the prerequisite steps really do gate them.
 *
 * THE EDGES ARE THE CLAIM, AND THEY ARE NOT ALL THE SAME CLAIM.
 *
 * This is the one place the drawing could quietly lie, because an arrow reads
 * as "you must". Three kinds, and the component draws each differently:
 *
 *   required  A stated requirement of the programme itself. You cannot enter
 *             ISEF without winning an affiliated fair; a teacher, not you,
 *             submits a Lemelson InvenTeam grant. These come from
 *             opportunities.entry_gate and the programme's own entry_note, so
 *             they are facts and are drawn solid. Only prep -> application.
 *
 *   common    An authored generalisation: how students usually get from one
 *             thing to the next. Learn, then build, then publish, then apply.
 *             Twenty-four hand-written spines back this and public.outcomes has
 *             zero rows, so it is drawn dashed and the legend says "a common
 *             route, not a requirement", the same stance the step cards take
 *             with edge_reason (see AUTHORED_EDGES in app/plan/page.tsx).
 *
 *   anytime   Nothing gates it; it sits beside the trunk because it belongs to
 *             that stage, not because the trunk node unlocks it. The second
 *             learning resource, the proof missions, the cold email. Dotted.
 *
 * Nothing here is arranged for looks. A node's row is its position in the
 * ladder and a canopy column is one programme, prep step stacked directly above
 * the application it unlocks.
 */

import type { RoadmapHorizon, RoadmapStep } from "@/lib/api";

export type EdgeKind = "required" | "common" | "anytime";

export type NodeKind =
  | "root"
  | "learn"
  | "build"
  | "publish"
  | "gate"
  | "apply"
  | "mission"
  | "outreach"
  | "step"
  | "horizon";

export type TreeNode = {
  /** step_key, so a node maps 1:1 to the card below it. */
  key: string;
  title: string;
  nodeKind: NodeKind;
  /** Ladder position. Row 0 is the student, today. */
  row: number;
  /** Horizontal position as a percentage of the canvas width. */
  x: number;
  /** Trunk nodes are the work that compounds; branches hang off them. */
  weight: "trunk" | "branch";
  parent: string | null;
  edge: EdgeKind | null;
  step: RoadmapStep | null;
  opportunityId: string | null;
  /** Field colour, when the step points at an opportunity we know the field of. */
  field: string | null;
  note: string;
  /**
   * Overrides the generic kind label on the node's chip.
   *
   * Exists for the locked row: "LOCKED" under a column of applications, with no
   * edge reaching it, reads as a node the drawing forgot to connect. "GRADE 11"
   * says why there is no edge, nothing on this tree reaches it, only a
   * birthday does.
   */
  badge?: string;
};

export type RoadmapTree = {
  nodes: TreeNode[];
  /** Row count, so the caller can size the canvas. */
  rows: number;
};

export const TRUNK_X = 50;
export const LEFT_X = 17;
export const RIGHT_X = 83;

/**
 * Column centre for one of `count` canopy nodes.
 *
 * Spread is capped so two applications sit either side of the trunk rather than
 * hugging the walls with a cavern between them, and so four still fit.
 */
export function canopyX(index: number, count: number): number {
  if (count <= 1) return TRUNK_X;
  const span = Math.min(78, 26 * (count - 1));
  return TRUNK_X - span / 2 + (span * index) / (count - 1);
}

const ROOT_NOTE =
  "Everything above is reachable from here. Nothing on this tree needs money, " +
  "a parent who went to college, or a teacher who already knows about it.";

export function buildRoadmapTree(
  steps: RoadmapStep[],
  options: {
    /** Field of an opportunity, for colour. Usually built from /matches. */
    fieldOf?: (opportunityId: string) => string | undefined;
    horizon?: RoadmapHorizon[];
    /**
     * Sub-steps a student asked for, keyed by the step they hang under.
     *
     * Drawn as a cluster off their parent with an "anytime" edge, because
     * that is what they are: the inside of a step you have already decided to
     * take. They are not another route through the tree, so they never become
     * trunk nodes and never adopt the applications.
     */
    branches?: Record<string, { title: string; detail: string }[]>;
    divergences?: Record<string, { title: string; detail: string }[]>;
  } = {},
): RoadmapTree {
  const fieldOf = options.fieldOf ?? (() => undefined);
  const nodes: TreeNode[] = [];
  const placed = new Set<string>();

  const push = (node: TreeNode) => {
    nodes.push(node);
    if (node.step) placed.add(node.step.step_key);
  };

  const colour = (step: RoadmapStep): string | null =>
    (step.opportunity_id ? fieldOf(step.opportunity_id) : undefined) ?? null;

  push({
    key: "root",
    title: "You, today",
    nodeKind: "root",
    row: 0,
    x: TRUNK_X,
    weight: "trunk",
    parent: null,
    edge: null,
    step: null,
    opportunityId: null,
    field: null,
    note: ROOT_NOTE,
  });

  let row = 1;
  let trunk = "root";

  const learn = steps.filter((s) => s.step_key.startsWith("learn:"));
  const project = steps.find((s) => s.step_key === "spine:project") ?? null;
  const publish = steps.find((s) => s.step_key === "spine:publish") ?? null;
  const missions = steps.filter((s) => s.step_key.startsWith("mission:"));
  const outreach = steps.filter((s) => s.step_key.startsWith("outreach:"));

  /** prep:<opportunity_id> — the step that unlocks an application. */
  const preps = new Map<string, RoadmapStep>();
  for (const step of steps) {
    if (step.step_key.startsWith("prep:")) {
      preps.set(step.opportunity_id ?? step.step_key.slice(5), step);
    }
  }
  const applications = steps
    .filter((s) => s.category === "application")
    .slice()
    .sort((a, b) => a.due_in_months - b.due_in_months);

  const stages: {
    step: RoadmapStep | null;
    kind: NodeKind;
    sides: RoadmapStep[];
    sideKind: NodeKind;
    side: "left" | "right";
  }[] = [
    {
      step: learn[0] ?? null,
      kind: "learn",
      sides: learn.slice(1),
      sideKind: "learn",
      side: "right",
    },
    {
      step: project,
      kind: "build",
      // NO MISSIONS ON THE TREE.
      //
      // They were drawn as branches off Build, which put two more cards on an
      // already crowded left margin for work the page has ALREADY listed:
      // MissionBoard renders the same missions, with their descriptions and a
      // completion control, directly above this figure. The tree was repeating
      // it in a form you cannot act on.
      //
      // They are still in `steps` and still reach the list below, so nothing
      // is lost, the orphan sweep further down picks up anything this layout
      // declines to place, which is exactly what it is for.
      sides: [],
      sideKind: "mission",
      side: "left",
    },
    {
      step: publish,
      kind: "publish",
      sides: outreach,
      sideKind: "outreach",
      side: "right",
    },
  ];

  for (const stage of stages) {
    const start = row;
    if (stage.step) {
      push({
        key: stage.step.step_key,
        title: stage.step.title,
        nodeKind: stage.kind,
        row: start,
        x: TRUNK_X,
        weight: "trunk",
        parent: trunk,
        // The spine's own claim about itself: learn makes the build possible,
        // and work nobody can see is hard to point at later. Authored, so
        // dashed.
        edge: "common",
        step: stage.step,
        opportunityId: stage.step.opportunity_id,
        field: colour(stage.step),
        note: stage.step.edge_note,
      });
      trunk = stage.step.step_key;
    }
    // A stage with no trunk step still has its branches: a student with no
    // charted path has no build step, and their missions must not vanish, they
    // hang off wherever the trunk has reached.
    const parent = stage.step ? stage.step.step_key : trunk;
    stage.sides.forEach((side, index) => {
      push({
        key: side.step_key,
        title: side.title,
        nodeKind: stage.sideKind,
        row: start + index,
        x: stage.side === "left" ? LEFT_X : RIGHT_X,
        weight: "branch",
        parent,
        edge: "anytime",
        step: side,
        opportunityId: side.opportunity_id,
        field: colour(side),
        note: side.edge_note,
      });
    });
    row = start + Math.max(stage.step ? 1 : 0, stage.sides.length);
  }

  // Anything roadmap.py emits that this layout does not recognise. Without
  // this a new step kind would silently disappear from the picture while still
  // appearing in the list underneath, which is the worst of both: a student
  // would see a step with no place on their own map.
  for (const step of steps) {
    if (placed.has(step.step_key)) continue;
    if (step.category === "application") continue;
    if (step.step_key.startsWith("prep:")) continue;
    // Missions are deliberately not on this tree (see the build stage above).
    // Without this they fall through here, become TRUNK nodes, and the
    // applications then hang off a mission instead of off publish, which is
    // worse than the clutter the exclusion was meant to remove.
    if (step.step_key.startsWith("mission:")) continue;
    push({
      key: step.step_key,
      title: step.title,
      nodeKind: "step",
      row,
      x: TRUNK_X,
      weight: "trunk",
      parent: trunk,
      edge: "anytime",
      step,
      opportunityId: step.opportunity_id,
      field: colour(step),
      note: step.edge_note,
    });
    trunk = step.step_key;
    row += 1;
  }

  // Sub-steps, hung under whichever node the student opened.
  //
  // Placed after the stages and before the canopy so they sit beside the
  // trunk they belong to rather than among the programmes. Each cluster is
  // laid out on its parent's free side: the learn branch already uses the
  // right, so these take the left, which is empty now that missions are not
  // drawn here.
  // The canopy: what the ladder is for. One column per programme, the gate
  // stacked directly above the application it opens.
  if (applications.length) {
    const gated = applications.some((a) => preps.has(a.opportunity_id ?? ""));
    const gateRow = row;
    const applyRow = gated ? row + 1 : row;
    applications.forEach((application, index) => {
      const x = canopyX(index, applications.length);
      const prep = preps.get(application.opportunity_id ?? "");
      if (prep) {
        push({
          key: prep.step_key,
          title: prep.title,
          nodeKind: "gate",
          row: gateRow,
          x,
          weight: "branch",
          parent: trunk,
          edge: "common",
          step: prep,
          opportunityId: prep.opportunity_id,
          field: colour(prep),
          note: prep.edge_note,
        });
      }
      push({
        key: application.step_key,
        title: application.title,
        nodeKind: "apply",
        row: applyRow,
        x,
        weight: "branch",
        parent: prep ? prep.step_key : trunk,
        // The gate is a rule the programme published. Everything else about
        // reaching an application is us generalising.
        edge: prep ? "required" : "common",
        step: application,
        opportunityId: application.opportunity_id,
        field: colour(application),
        note: application.edge_note,
      });
    });
    row = applyRow + 1;
  }

  // Locked programmes. Drawn with no edge at all, because there is no step that
  // reaches them, only a birthday.
  const horizon = (options.horizon ?? []).slice(0, 4);
  if (horizon.length) {
    const horizonRow = row;
    horizon.forEach((item, index) => {
      push({
        key: `horizon:${item.opportunity_id}`,
        title: item.title,
        nodeKind: "horizon",
        row: horizonRow,
        x: canopyX(index, horizon.length),
        weight: "branch",
        parent: null,
        edge: null,
        step: null,
        opportunityId: item.opportunity_id,
        field: fieldOf(item.opportunity_id) ?? null,
        note: item.edge_note,
        badge: `Grade ${item.opens_at_grade}`,
      });
    });
    row = horizonRow + 1;
  }

  // AFTER THE CANOPY, and that is the whole point.
  //
  // These ran before it, so a breakdown hanging off an application step could
  // not find its parent -- the canopy nodes did not exist yet -- and was
  // dropped. The step list rendered the sub-steps and the diagram did not,
  // which reads as a cosmetic glitch and is actually a missing node.
  // Everything a branch can hang off now exists before this runs.
  // A sub-step can be broken down too, so a parent here may itself be a branch
  // node created by an earlier pass. Object key order is not guaranteed to put
  // a parent before its child, so iterate by DEPTH: every node at depth n
  // exists before anything at depth n+1 looks for it. Without this, opening a
  // sub-step's sub-steps worked or silently vanished depending on insertion
  // order, which is the worst of both.
  const branches = options.branches ?? {};
  const depthOf = (key: string) => key.split("::branch:").length - 1;
  const byDepth = Object.keys(branches).sort(
    (a, b) => depthOf(a) - depthOf(b),
  );

  for (const parentKey of byDepth) {
    const subSteps = branches[parentKey];
    const parent = nodes.find((n) => n.key === parentKey);
    if (!parent || !subSteps?.length) continue;
    // Each generation steps further out from the trunk so a sub-step's own
    // sub-steps do not land on top of their aunts. Depth is capped at
    // BRANCH_MAX_DEPTH where the control is drawn, so this cannot walk off the
    // canvas.
    const depth = depthOf(parentKey) + 1;
    const outward = Math.min(depth - 1, 2) * 6;
    const side = parent.x <= TRUNK_X ? "right" : "left";
    subSteps.slice(0, 3).forEach((sub, index) => {
      nodes.push({
        key: `${parentKey}::branch:${index}`,
        title: sub.title,
        nodeKind: "step",
        row: parent.row + index,
        x:
          side === "left"
            ? Math.max(4, LEFT_X - outward)
            : Math.min(96, RIGHT_X + outward),
        weight: "branch",
        parent: parentKey,
        edge: "anytime",
        step: null,
        opportunityId: null,
        field: parent.field,
        note: sub.detail,
      });
    });
    row = Math.max(row, parent.row + subSteps.length);
  }

  // Forks: other directions out of a step, drawn beside it rather than under
  // it. Dotted, the weakest edge the tree has, because nothing here is
  // required and nobody has measured that students take it. Placed on the
  // parent's own side so a fork reads as "instead of this" rather than
  // "after this", which is what the sub-steps opposite already say.
  const divergences = options.divergences ?? {};
  for (const [parentKey, forks] of Object.entries(divergences)) {
    const parent = nodes.find((n) => n.key === parentKey);
    if (!parent || !forks.length) continue;
    forks.slice(0, 3).forEach((fork, index) => {
      nodes.push({
        key: `${parentKey}::diverge:${index}`,
        title: fork.title,
        nodeKind: "step",
        row: parent.row + index,
        x: parent.x === TRUNK_X
          ? LEFT_X
          : parent.x < TRUNK_X
            ? Math.max(4, parent.x - 11)
            : Math.min(96, parent.x + 11),
        weight: "branch",
        parent: parentKey,
        edge: "anytime",
        step: null,
        opportunityId: null,
        field: parent.field,
        note: fork.detail,
        badge: "OR",
      });
    });
    row = Math.max(row, parent.row + forks.length);
  }

  return { nodes, rows: row };
}

/**
 * Where the student is.
 *
 * The first step on the tree, because roadmap_steps has no completed_at column
 * and nothing can be marked done. A map that claimed progress it cannot observe
 * would be worse than one that shows the start.
 */
export function firstActionable(tree: RoadmapTree): string | null {
  return tree.nodes.find((node) => node.step !== null)?.key ?? null;
}
