import { describe, expect, it } from "vitest";
import {
  buildRoadmapTree,
  canopyX,
  firstActionable,
  LEFT_X,
  RIGHT_X,
  TRUNK_X,
  type TreeNode,
} from "./roadmap-graph";
import type { RoadmapStep } from "./api";

function step(partial: Partial<RoadmapStep> & { step_key: string }): RoadmapStep {
  return {
    category: "skill",
    title: partial.step_key,
    edge_reason: "ladder",
    edge_note: "",
    opportunity_id: null,
    resource_id: null,
    mission_id: null,
    timeframe: "month",
    due_in_months: 0,
    phase_index: 0,
    phase_label: "Now",
    ordinal: 0,
    ...partial,
  } as RoadmapStep;
}

/** A plan shaped like the one roadmap.py actually emits. */
function fullPlan(): RoadmapStep[] {
  return [
    step({ step_key: "learn:r1", title: "Start Khan Academy stats" }),
    step({ step_key: "learn:r2", title: "Then OpenIntro" }),
    step({ step_key: "spine:project", category: "project", title: "Build the thing", edge_reason: "artifact" }),
    step({ step_key: "spine:publish", category: "project", title: "Publish it", edge_reason: "evidence" }),
    step({ step_key: "mission:m1", category: "project", title: "Mission one", due_in_months: 3 }),
    step({ step_key: "prep:opp-a", opportunity_id: "opp-a", title: "Qualify first", edge_reason: "gate", due_in_months: 1.99 }),
    step({ step_key: "qualify:opp-a", category: "application", opportunity_id: "opp-a", title: "Enter USAMO", edge_reason: "gate", due_in_months: 2 }),
    step({ step_key: "apply:opp-b", category: "application", opportunity_id: "opp-b", title: "Apply to RSI", edge_reason: "window", due_in_months: 5 }),
    step({ step_key: "outreach:cold-email", category: "outreach", title: "Email two people", due_in_months: 2 }),
  ];
}

const byKey = (nodes: TreeNode[]) =>
  new Map(nodes.map((node) => [node.key, node]));

describe("buildRoadmapTree", () => {
  it("places every step on the tree exactly once", () => {
    const steps = fullPlan();
    const { nodes } = buildRoadmapTree(steps);
    const keys = nodes.filter((n) => n.step).map((n) => n.key);
    expect(new Set(keys).size).toBe(keys.length);
    for (const s of steps) {
      // Missions are the one deliberate omission; see the dedicated test.
      if (s.step_key.startsWith("mission:")) continue;
      expect(keys).toContain(s.step_key);
    }
  });

  it("never drops a step kind the layout does not recognise", () => {
    // The guard that matters: roadmap.py gains a step and the picture keeps it
    // rather than showing a student a card with no place on their own map.
    const steps = [...fullPlan(), step({ step_key: "reflect:journal", title: "Write up what changed" })];
    const { nodes } = buildRoadmapTree(steps);
    const node = byKey(nodes).get("reflect:journal");
    expect(node).toBeDefined();
    expect(node?.nodeKind).toBe("step");
  });

  it("gates an application behind its prep step, and says that is required", () => {
    const { nodes } = buildRoadmapTree(fullPlan());
    const map = byKey(nodes);
    const gated = map.get("qualify:opp-a");
    expect(gated?.parent).toBe("prep:opp-a");
    expect(gated?.edge).toBe("required");
    // The prep step sits in the same column, one row above.
    expect(map.get("prep:opp-a")?.x).toBe(gated?.x);
    expect(map.get("prep:opp-a")?.row).toBe((gated?.row ?? 0) - 1);
  });

  it("marks an ungated application as a common route, not a requirement", () => {
    const { nodes } = buildRoadmapTree(fullPlan());
    const open = byKey(nodes).get("apply:opp-b");
    expect(open?.edge).toBe("common");
    expect(open?.parent).toBe("spine:publish");
  });

  it("chains the spine learn -> build -> publish down the trunk", () => {
    const { nodes } = buildRoadmapTree(fullPlan());
    const map = byKey(nodes);
    expect(map.get("learn:r1")?.parent).toBe("root");
    expect(map.get("spine:project")?.parent).toBe("learn:r1");
    expect(map.get("spine:publish")?.parent).toBe("spine:project");
    for (const key of ["learn:r1", "spine:project", "spine:publish"]) {
      expect(map.get(key)?.x).toBe(TRUNK_X);
      expect(map.get(key)?.weight).toBe("trunk");
    }
    // Strictly increasing rows: further up the tree really is later.
    expect(map.get("spine:project")!.row).toBeGreaterThan(map.get("learn:r1")!.row);
    expect(map.get("spine:publish")!.row).toBeGreaterThan(map.get("spine:project")!.row);
  });

  it("hangs ungated work off the side, dotted", () => {
    const { nodes } = buildRoadmapTree(fullPlan());
    const map = byKey(nodes);
    expect(map.get("learn:r2")?.edge).toBe("anytime");
    expect(map.get("learn:r2")?.x).toBe(RIGHT_X);
    expect(map.get("outreach:cold-email")?.edge).toBe("anytime");
  });

  it("draws missions as branches, each on a row of its own", () => {
    // They were excluded entirely, because falling through the trunk loop made
    // them trunk nodes and the applications then hung off a mission instead of
    // off publish. Placing them as branches is the fix; leaving them off the
    // diagram was only a workaround.
    const { nodes } = buildRoadmapTree(fullPlan());
    const missions = nodes.filter((n) => n.nodeKind === "mission");
    expect(missions.length).toBeGreaterThan(0);
    for (const mission of missions) {
      expect(mission.weight).toBe("branch");
      expect(mission.edge).toBe("anytime");
      // Nothing else may share the row, which is what kept them clear of the
      // canopy columns.
      const sharing = nodes.filter(
        (n) => n.row === mission.row && n.key !== mission.key,
      );
      expect(sharing, `row ${mission.row}`).toHaveLength(0);
    }
  });

  it("keeps a sided step when there is no trunk step to hang it on", () => {
    // "None of these are me" with no generated spine yet: no spine:project.
    // The branch still has to land somewhere rather than vanish, it hangs
    // off wherever the trunk has reached. Written with outreach now that
    // missions are off the tree entirely.
    const steps = [
      step({ step_key: "learn:r1" }),
      step({ step_key: "outreach:cold-email", category: "outreach", title: "Email two people" }),
    ];
    const { nodes } = buildRoadmapTree(steps);
    const outreach = byKey(nodes).get("outreach:cold-email");
    expect(outreach).toBeDefined();
    expect(outreach?.parent).toBe("learn:r1");
  });

  it("builds a tree from nothing but a root", () => {
    const { nodes, rows } = buildRoadmapTree([]);
    expect(nodes).toHaveLength(1);
    expect(nodes[0].key).toBe("root");
    expect(rows).toBe(1);
  });

  it("orders the canopy by closing date, left to right", () => {
    const { nodes } = buildRoadmapTree(fullPlan());
    const canopy = nodes.filter((n) => n.nodeKind === "apply");
    expect(canopy.map((n) => n.key)).toEqual(["qualify:opp-a", "apply:opp-b"]);
    expect(canopy[0].x).toBeLessThan(canopy[1].x);
  });

  it("draws locked programmes with no edge, because no step reaches them", () => {
    const { nodes } = buildRoadmapTree(fullPlan(), {
      horizon: [
        {
          title: "RSI",
          opens_at_grade: 11,
          opportunity_id: "opp-c",
          edge_reason: "eligibility",
          edge_note: "Opens when you reach grade 11.",
        },
      ],
    });
    const locked = byKey(nodes).get("horizon:opp-c");
    expect(locked?.edge).toBeNull();
    expect(locked?.parent).toBeNull();
    expect(locked?.nodeKind).toBe("horizon");
  });

  it("tells a locked node why nothing reaches it", () => {
    // Drawn with no edge, which without the grade on its chip reads as a node
    // the picture forgot to connect rather than one a birthday unlocks.
    const { nodes } = buildRoadmapTree(fullPlan(), {
      horizon: [
        {
          title: "MIT PRIMES",
          opens_at_grade: 11,
          opportunity_id: "opp-c",
          edge_reason: "eligibility",
          edge_note: "",
        },
      ],
    });
    expect(byKey(nodes).get("horizon:opp-c")?.badge).toBe("Grade 11");
  });

  it("colours a node only when the field is actually known", () => {
    const { nodes } = buildRoadmapTree(fullPlan(), {
      fieldOf: (id) => (id === "opp-a" ? "math" : undefined),
    });
    const map = byKey(nodes);
    expect(map.get("qualify:opp-a")?.field).toBe("math");
    expect(map.get("apply:opp-b")?.field).toBeNull();
    expect(map.get("spine:project")?.field).toBeNull();
  });

  it("every node but the root and the horizon has a parent that exists", () => {
    const { nodes } = buildRoadmapTree(fullPlan());
    const keys = new Set(nodes.map((n) => n.key));
    for (const node of nodes) {
      if (node.parent === null) continue;
      expect(keys.has(node.parent)).toBe(true);
    }
  });

  it("never puts two nodes close enough to overlap on the same row", () => {
    // The nodes are absolutely positioned, so nothing stops them colliding
    // except this. 158px is the widest branch node on a 736px canvas floor,
    // which is 21%, so columns must stay further apart than that.
    const { nodes } = buildRoadmapTree(fullPlan(), {
      horizon: [1, 2, 3, 4].map((n) => ({
        title: `Locked ${n}`,
        opens_at_grade: 11,
        opportunity_id: `opp-locked-${n}`,
        edge_reason: "eligibility",
        edge_note: "",
      })),
    });
    const rows = new Map<number, number[]>();
    for (const node of nodes) {
      rows.set(node.row, [...(rows.get(node.row) ?? []), node.x]);
    }
    for (const [row, xs] of rows) {
      const sorted = [...xs].sort((a, b) => a - b);
      for (let i = 1; i < sorted.length; i += 1) {
        expect(
          sorted[i] - sorted[i - 1],
          `row ${row} columns ${sorted[i - 1]} and ${sorted[i]}`,
        ).toBeGreaterThanOrEqual(22);
      }
    }
  });

  it("parents are always at or above their children, never below", () => {
    const { nodes } = buildRoadmapTree(fullPlan());
    const map = byKey(nodes);
    for (const node of nodes) {
      if (!node.parent) continue;
      expect(map.get(node.parent)!.row).toBeLessThanOrEqual(node.row);
    }
  });
});

describe("canopyX", () => {
  it("centres a single column on the trunk", () => {
    expect(canopyX(0, 1)).toBe(TRUNK_X);
  });

  it("keeps a pair either side of the trunk rather than at the walls", () => {
    expect(canopyX(0, 2)).toBe(37);
    expect(canopyX(1, 2)).toBe(63);
  });

  it("fits four columns inside the canvas", () => {
    for (let i = 0; i < 4; i += 1) {
      expect(canopyX(i, 4)).toBeGreaterThanOrEqual(8);
      expect(canopyX(i, 4)).toBeLessThanOrEqual(92);
    }
  });
});

describe("firstActionable", () => {
  it("is the first real step, not the root", () => {
    expect(firstActionable(buildRoadmapTree(fullPlan()))).toBe("learn:r1");
  });

  it("is nothing when there are no steps", () => {
    expect(firstActionable(buildRoadmapTree([]))).toBeNull();
  });
});

describe("branches attach to every kind of node", () => {
  // The bug this pins: the branch loop ran before the canopy was built, so a
  // breakdown on an application step could not find its parent and was
  // dropped. The list showed the sub-steps and the diagram did not.
  const steps: RoadmapStep[] = [
    {
      step_key: "spine:project",
      title: "Build the thing",
      category: "project",
      due_in_months: 1,
    } as RoadmapStep,
    {
      step_key: "apply:aaa",
      title: "Apply to the programme",
      category: "application",
      due_in_months: 3,
      opportunity_id: "aaa",
    } as RoadmapStep,
  ];

  it.each([["spine:project"], ["apply:aaa"]])(
    "draws a breakdown hanging off %s",
    (parentKey) => {
      const tree = buildRoadmapTree(steps, {
        branches: {
          [parentKey]: [
            { title: "First move", detail: "d" },
            { title: "Second move", detail: "d" },
          ],
        },
      });
      // By key prefix, not by parent: a real step can legitimately parent
      // other steps (an application hangs off the trunk), and this is
      // asserting the sub-steps specifically.
      const kids = tree.nodes.filter((n) =>
        n.key.startsWith(`${parentKey}::branch:`),
      );
      expect(kids.map((k) => k.title)).toEqual(["First move", "Second move"]);
    },
  );

  it("draws a divergence hanging off an application too", () => {
    const tree = buildRoadmapTree(steps, {
      divergences: {
        "apply:aaa": [
          { title: "Or do this", detail: "d" },
          { title: "Or that", detail: "d" },
        ],
      },
    });
    const forks = tree.nodes.filter((n) =>
      n.key.startsWith("apply:aaa::diverge:"),
    );
    expect(forks).toHaveLength(2);
    expect(forks[0].badge).toBe("OR");
  });
});
