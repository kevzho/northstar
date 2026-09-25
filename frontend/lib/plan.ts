/**
 * 30-day plan generation — turns a chosen future path into concrete actions.
 *
 * The plan used to be a hardcoded list, identical for every student. It is now
 * assembled from three inputs the app already computes, by rules simple enough
 * to explain out loud:
 *
 *   1. The chosen archetype supplies the spine: a starter project, a way to
 *      publish it, and a skill sprint — one entry per archetype below.
 *   2. The trait profile bends the plan: the strongest trait gets a lean-in
 *      action, the weakest gets a stretch action.
 *   3. Real matches (when signed in) supply application targets: the top-scored
 *      opportunities, with actual deadlines, sorted so the soonest lands in
 *      week one and the rest in week four.
 *
 * Everything is a pure function of (path, traits, matches, today) so the rules
 * are trivially testable and every line of output can be traced to an input.
 */

import type { TraitKey } from "./assessment";
import { traitLabels } from "./assessment";
import type { Archetype } from "./archetypes";
import { archetypes } from "./archetypes";
import type { MatchResult } from "./types";
import type { PathKind, TraitScores } from "./scoring";
import { TRAIT_KEYS } from "./scoring";

export type PlanGroup = {
  timeframe: string;
  focus: string;
  items: string[];
};

/** Archetype-specific spine: project, publish step, and skill sprint. */
const SPINES: Record<
  string,
  { project: string; publish: string; skill: string; skillKey: string }
> = {
  "applied-ai-builder": {
    project:
      "Build a small AI tool that removes one annoyance from your own week — a study-note summarizer, a flashcard generator — and get it working end to end, however rough.",
    publish:
      "Record a 60-second demo of the tool and post it where other builders will actually see it.",
    skill:
      "evaluation — learn to measure whether an AI feature actually works, not just whether it runs",
    skillKey: "evaluation",
  },
  "computational-biology-researcher": {
    project:
      "Pick one public dataset (NCBI, a Kaggle bio set) and reproduce one figure or statistic from a real paper with your own code.",
    publish:
      "Write a short lab-notebook post: what the data showed, what surprised you, what you would test next.",
    skill: "statistics — the hypothesis tests behind the figure you reproduced",
    skillKey: "statistics",
  },
  "technical-founder": {
    project:
      "Interview five people about one problem you suspect they share, then build the smallest thing that addresses it.",
    publish:
      "Ship a one-page site for the idea and get ten people to react to it.",
    skill: "scoping — cutting an idea down to a one-week MVP without losing it",
    skillKey: "scoping",
  },
  "product-minded-engineer": {
    project:
      "Take a tool you already use daily and redesign the one workflow that annoys you — write the spec first, then build the improvement.",
    publish:
      "Post a before/after write-up showing the redesign and the reasoning behind each change.",
    skill:
      "user research — turning three real user conversations into one prioritized change",
    skillKey: "user-research",
  },
  "civic-technology-designer": {
    project:
      "Find one local problem — school, library, community org — and prototype a tool that helps, together with the people who would use it.",
    publish:
      "Present the prototype to the group it serves and collect their reactions in writing.",
    skill: "accessibility — making the prototype usable by everyone it is for",
    skillKey: "accessibility",
  },
  "research-mathematician": {
    project:
      "Pick one competition problem set (AMC, a past olympiad) and write full solutions to five problems — proofs, not answers.",
    publish:
      "Write up your cleanest proof and post it where other math students will critique it.",
    skill: "proof technique — induction and contradiction until they are reflexes",
    skillKey: "proof-technique",
  },
  "experimental-physicist": {
    project:
      "Design and run one tabletop experiment with real measurements — pendulum period, diffraction, cooling curves — and compare against theory.",
    publish:
      "Write a short lab report: setup, data, error sources, and where theory and measurement disagreed.",
    skill: "error analysis — knowing how much to trust every number you record",
    skillKey: "error-analysis",
  },
  "robotics-engineer": {
    project:
      "Build one mechanism that moves under its own control — a line follower, a sorting arm, a self-balancing something — however rough.",
    publish:
      "Record it working (and failing) and post the build log with what broke.",
    skill: "control basics — why the naive approach oscillates and PID doesn't",
    skillKey: "control-basics",
  },
  "biomedical-innovator": {
    project:
      "Pick one health problem someone you know actually has and prototype the smallest device, tool, or protocol that helps.",
    publish:
      "Show it to one person in healthcare — a nurse, a PT, a school counselor — and write down their reaction.",
    skill: "regulatory literacy — why medical ideas move slowly and what that means for design",
    skillKey: "regulatory-literacy",
  },
  "data-scientist": {
    project:
      "Take one public dataset about your own city or school district and answer a question nobody has asked it yet.",
    publish:
      "Publish the notebook with three charts and one honest paragraph about what the data cannot say.",
    skill: "statistical honesty — confounders, base rates, and when a trend is noise",
    skillKey: "statistical-honesty",
  },
  "science-communicator": {
    project:
      "Take one paper or result you love and produce a two-minute explanation a ninth grader would finish.",
    publish:
      "Post it publicly and ask three non-STEM friends what they understood — revise until they can repeat it back.",
    skill: "narrative structure — hook, stakes, one idea, and nothing else",
    skillKey: "narrative-structure",
  },
  "field-research-scientist": {
    project:
      "Design a four-week observation protocol for something living or changing near you — a creek, a tree line, night sky brightness — and collect real data on schedule.",
    publish:
      "Publish the dataset with your protocol so someone else could repeat it.",
    skill: "sampling discipline — why the boring schedule is the whole experiment",
    skillKey: "sampling-discipline",
  },
  "game-designer": {
    project:
      "Make one level of one mechanic — not a game, a level — and put it in front of three people who did not watch you build it.",
    publish:
      "Post the level with a short note on the one change you made after watching someone play it badly.",
    skill:
      "playtesting — learning to watch someone struggle without jumping in to help them",
    skillKey: "playtesting",
  },
  "product-designer": {
    project:
      "Take one screen of an app your school actually makes you use and redesign it — write down what each element is for before you move anything.",
    publish:
      "Post the before, the after, and the reasoning for each change you kept and each one you abandoned.",
    skill:
      "critique — separating what you like from what works, in your own designs and other people's",
    skillKey: "design-critique",
  },
  "digital-media-artist": {
    project:
      "Build one piece where the medium is the point — generative, interactive, or time-based — and get it running somewhere a stranger can open it.",
    publish:
      "Publish it with a process note: what you tried first, why it failed, and what the failure taught you about the medium.",
    skill:
      "colour and contrast — why a palette reads instantly to everyone or quietly excludes people",
    skillKey: "colour-contrast",
  },
  "social-entrepreneur": {
    project:
      "Pick one problem you have watched someone live with, then find the five organisations already working on it and write down honestly what is missing.",
    publish:
      "Share the map — who is doing what, where the gap is, and what you would try first with no money.",
    skill:
      "unit economics — working out what one unit of the change you want actually costs to deliver",
    skillKey: "unit-economics",
  },
  "quantitative-economist": {
    project:
      "Take one public dataset about something you care about and answer one question with it — then write down every reason your answer might be wrong.",
    publish:
      "Post the chart, the code, and the caveats, with the caveats given as much room as the finding.",
    skill:
      "causal inference — why a correlation in observational data is almost never the answer to a policy question",
    skillKey: "causal-inference",
  },
  "investigative-journalist": {
    project:
      "Find one claim being repeated locally that nobody has checked, and go check it against a primary source — a budget, a filing, a dataset.",
    publish:
      "Write it up in 600 words, link every source, and state plainly what you could not confirm.",
    skill:
      "public records — finding the document that already exists and that nobody has read",
    skillKey: "public-records",
  },
  "science-policy-advocate": {
    project:
      "Read one real bill that touches science or health, all the way through, and write a one-page brief on what it actually does versus what it is described as doing.",
    publish:
      "Send the brief to someone whose job it is to care — a staffer, a local reporter, a teacher — and ask for one correction.",
    skill:
      "legislative reading — how a bill is structured, where the money is, and which clause does the real work",
    skillKey: "legislative-reading",
  },
  "public-health-strategist": {
    project:
      "Pick one health outcome in your own county, find its rate, and compare it to the state — then work out what would have to be true for the difference to be real.",
    publish:
      "Publish the comparison with the denominator stated as prominently as the number.",
    skill:
      "rates and denominators — why per-100,000 and age-adjustment routinely reverse the obvious answer",
    skillKey: "rates-denominators",
  },
  "sports-scientist": {
    project:
      "Measure one thing about one athlete — yourself counts — across two weeks, on a schedule you commit to before you start.",
    publish:
      "Post the data and the protocol, including the sessions you missed and what that does to the conclusion.",
    skill:
      "measurement validity — checking that your instrument measures the thing you think it measures",
    skillKey: "measurement-validity",
  },
  "bioethicist": {
    project:
      "Take one live disagreement in biology or medicine and write the strongest version of the argument you disagree with, in its own terms.",
    publish:
      "Publish both sides mapped out — claims, premises, and the assumption each side will not give up.",
    skill:
      "argument mapping — pulling a claim apart into its premises and finding the one nobody is defending",
    skillKey: "argument-mapping",
  },
  "edtech-creator": {
    project:
      "Teach one specific thing to one specific person who does not get it yet, then rebuild your explanation after watching where they stalled.",
    publish:
      "Ship the explanation as something reusable — a page, a worksheet, a small tool — and note what you cut.",
    skill:
      "learning science — spacing, retrieval practice, and why re-reading feels productive and mostly is not",
    skillKey: "learning-science",
  },
  "conservation-storyteller": {
    project:
      "Document one species or one place near you over two weeks, with your own observations, and get one fact checked by someone who studies it.",
    publish:
      "Publish the piece with your field notes attached, so the reader can see what you saw and what you inferred.",
    skill:
      "getting the biology right — reading a species account well enough that a specialist would not wince",
    skillKey: "species-accuracy",
  },
};

const FALLBACK_SPINE = {
  project:
    "Build a tiny portfolio project that could only belong to this path — small enough to finish, real enough to show.",
  publish: "Publish the project with a short demo note explaining what it does.",
  skill: "the one skill gap standing between you and the next version of this project",
};

/** Lean-in actions, keyed by the student's strongest trait. */
const LEAN_IN: Record<TraitKey, string> = {
  builder:
    "Let building lead: start with working code, and write the explanation after it runs.",
  analyst:
    "Let analysis lead: before building, spend one session mapping what is actually known about the problem.",
  riskTolerance:
    "Use your risk appetite: pick the more ambitious version of the project while the month is young.",
  ambiguityComfort:
    "Use your comfort with open problems: choose the fuzzy version of the project others would avoid.",
  collaboration:
    "Recruit one classmate into the project this week — you work best with others in the loop.",
  executionTempo:
    "Set a shipping rhythm now: something visible every Friday, even if small.",
};

/** Stretch actions, keyed by the student's weakest trait. */
const STRETCH: Record<TraitKey, string> = {
  builder:
    "Stretch goal: turn one idea into running code this month, however small — momentum beats polish.",
  analyst:
    "Stretch goal: write down, with numbers, how you will know the project worked.",
  riskTolerance:
    "Stretch goal: do one thing this month that might visibly fail — apply anyway, post anyway.",
  ambiguityComfort:
    "Stretch goal: start one task before you feel ready for it; write down what was unclear and when it resolved.",
  collaboration:
    "Stretch goal: show unfinished work to one person and ask for criticism, not praise.",
  executionTempo:
    "Stretch goal: timebox — give the first version of the project exactly one week, then stop and assess.",
};

function formatDeadline(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

/** Days from `today` to an ISO date, negative when past. */
function daysUntil(iso: string, today: Date): number {
  return Math.ceil(
    (new Date(iso).getTime() - today.getTime()) / (1000 * 60 * 60 * 24),
  );
}

export function findArchetype(id: string): Archetype | null {
  return archetypes.find((a) => a.id === id) ?? null;
}

export function generatePlan(
  archetype: Archetype,
  kind: PathKind,
  traits: TraitScores,
  matches: MatchResult[] | null,
  today: Date,
): PlanGroup[] {
  const spine = SPINES[archetype.id] ?? FALLBACK_SPINE;

  const ordered = [...TRAIT_KEYS].sort((a, b) => traits[b] - traits[a]);
  const strongest = ordered[0];
  const weakest = ordered[ordered.length - 1];

  // Application targets: top two matches by score, plus the best-scored
  // competition or scholarship if the top two didn't include one — every
  // voyage should have at least one award to compete for. Anything due
  // inside the month is urgent (week one); the rest belong to week four.
  const ranked = matches ?? [];
  const targets = ranked.slice(0, 2);
  if (
    ranked.length > 2 &&
    !targets.some((m) =>
      ["competition", "scholarship"].includes(m.opportunity.type),
    )
  ) {
    const award = ranked.find((m) =>
      ["competition", "scholarship"].includes(m.opportunity.type),
    );
    if (award) targets.push(award);
    else targets.push(ranked[2]);
  } else if (ranked.length > 2) {
    targets.push(ranked[2]);
  }
  const urgent = targets.filter(
    (m) =>
      m.opportunity.deadline !== null &&
      daysUntil(m.opportunity.deadline, today) <= 30 &&
      daysUntil(m.opportunity.deadline, today) >= 0,
  );
  const later = targets.filter((m) => !urgent.includes(m));

  const week1: string[] = [
    `Set your heading: write three sentences on why ${archetype.label} is your ${
      kind === "safe" ? "closest" : kind === "ambitious" ? "stretch" : "wildcard"
    } destination — you will reread this on arrival.`,
    spine.project,
    LEAN_IN[strongest],
  ];
  for (const m of urgent) {
    week1.push(
      `Launch-window alert: ${m.opportunity.title} closes ${formatDeadline(
        m.opportunity.deadline as string,
      )} — start the application now, not on arrival.`,
    );
  }

  const weeks23: string[] = [
    spine.publish,
    `Run a focused 5-hour sprint on ${spine.skill}.`,
    "Email two people doing work you want to do — a lab manager, a program director, a student who finished the thing. Ask one specific question each, not for generic advice.",
    STRETCH[weakest],
  ];

  const week4: string[] = [];
  if (later.length > 0) {
    for (const m of later) {
      week4.push(
        m.opportunity.deadline
          ? `Apply to ${m.opportunity.title} (deadline ${formatDeadline(
              m.opportunity.deadline,
            )}).`
          : `Apply to ${m.opportunity.title} (rolling deadline — sooner reads stronger).`,
      );
    }
  } else if (targets.length === 0) {
    week4.push(
      "Apply to one program, competition, or internship from your recommendations — sign in to see them ranked with deadlines.",
    );
  }
  week4.push(
    "Reread your launch note. Hold course, correct it, or chart a new destination — all three are progress.",
    "Log every application outcome in Northstar — each result re-weights the pathway map for you and the next student.",
  );

  return [
    { timeframe: "Leg 1 · Week 1", focus: "Launch", items: week1 },
    { timeframe: "Leg 2 · Weeks 2–3", focus: "Cruise", items: weeks23 },
    { timeframe: "Leg 3 · Week 4", focus: "Arrival", items: week4 },
  ];
}

// ---------------------------------------------------------------------------
// Persistence — the chosen path, same localStorage pattern as the assessment.
// ---------------------------------------------------------------------------

export const CHOSEN_PATH_KEY = "northstar.plan.chosen-path";

export type ChosenPath = { archetypeId: string; kind: PathKind };

const KINDS: PathKind[] = ["safe", "ambitious", "unconventional"];

/**
 * Parse a stored payload, dropping anything that no longer matches the
 * archetype library or the known path kinds. Pure so it is testable and safe
 * on the server; storage access lives in lib/use-chosen-path.ts.
 */
export function parseChosenPath(raw: string | null): ChosenPath | null {
  if (!raw) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== "object") return null;
  const { archetypeId, kind } = parsed as Record<string, unknown>;
  if (typeof archetypeId !== "string" || !findArchetype(archetypeId)) {
    return null;
  }
  if (typeof kind !== "string" || !KINDS.includes(kind as PathKind)) {
    return null;
  }
  return { archetypeId, kind: kind as PathKind };
}

export function traitLabel(trait: TraitKey): string {
  return traitLabels[trait];
}


/**
 * The learning-resource key for an archetype's skill rung.
 *
 * Joins SPINES[].skillKey to public.learning_resources.skill_key, so the plan
 * can show a student WHERE to learn the skill it tells them to learn. Returns
 * "" for the 12 archetypes that still fall through to FALLBACK_SPINE — those
 * have no authored skill rung yet, and an empty key means the plan renders
 * without a resource block rather than showing the wrong one.
 */
export function skillKeyFor(archetypeId: string): string {
  return SPINES[archetypeId]?.skillKey ?? "";
}


/** Archetype ids that have an authored spine. See lib/spines.test.ts. */
export const SPINE_KEYS = Object.keys(SPINES);

/** The authored spine for an archetype, or undefined if it would fall back. */
export function spineFor(archetypeId: string) {
  return SPINES[archetypeId];
}
