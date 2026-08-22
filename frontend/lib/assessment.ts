import type { OpportunityField } from "./types";

export type TraitKey =
  | "builder"
  | "analyst"
  | "riskTolerance"
  | "ambiguityComfort"
  | "collaboration"
  | "executionTempo";

export type TraitDeltas = Partial<Record<TraitKey, number>>;

export type FieldDeltas = Partial<Record<OpportunityField, number>>;

// ---------------------------------------------------------------------------
// The 1-5 agreement scale.
// ---------------------------------------------------------------------------

export const LIKERT_VALUES = [1, 2, 3, 4, 5] as const;

export type LikertValue = (typeof LIKERT_VALUES)[number];

export const likertLabels: Record<LikertValue, string> = {
  1: "Strongly disagree",
  2: "Disagree",
  3: "Neutral",
  4: "Agree",
  5: "Strongly agree",
};

/**
 * A rating's share of its question's deltas: 1 pays nothing, 5 pays in full,
 * 3 pays half. Keeping the multiplier in [0, 1] rather than [-1, 1] is what
 * lets Likert items reuse the same "sum, then divide by the achievable
 * maximum" normalization the choice questions already use — a trait can never
 * be driven negative, so the 0-100 range holds without clamping.
 *
 * Reverse-coded items invert it, so agreeing with "I need clear instructions"
 * pays *less* ambiguity comfort. Mixing a few of those in is what stops a
 * student who agrees with everything from scoring high on all six traits.
 */
export function likertWeight(value: LikertValue, reverse = false): number {
  const share = (value - 1) / 4;
  return reverse ? 1 - share : share;
}

export type AssessmentChoice = {
  id: string;
  label: string;
  traits: TraitDeltas;
  /** Field-interest weights; only the field-signal questions carry these. */
  fields?: FieldDeltas;
};

/**
 * Pick-one questions. Five options, never three: with three, a student who
 * is none of the three is forced to misreport, and the field percentages
 * inherit that noise.
 */
export type ChoiceQuestion = {
  kind: "choice";
  id: string;
  prompt: string;
  choices: AssessmentChoice[];
};

/** A statement rated 1-5. The deltas are what a "Strongly agree" pays out. */
export type LikertQuestion = {
  kind: "likert";
  id: string;
  prompt: string;
  traits: TraitDeltas;
  fields?: FieldDeltas;
  /** When true, disagreeing is what pays the deltas. */
  reverse?: boolean;
};

export type AssessmentQuestion = ChoiceQuestion | LikertQuestion;

/** One-line meanings shown under the profile bars — high is a shape,
 * not a grade; every trait names a way of working, not a virtue. */
export const traitDescriptions: Record<TraitKey, string> = {
  builder: "Defaults to making things — shipping beats theorizing.",
  analyst: "Leads with evidence, structure, and depth before acting.",
  riskTolerance:
    "Comfort betting effort on uncertain outcomes — entering what you might lose, launching before it is perfect.",
  ambiguityComfort:
    "Operates well without clear instructions or a known right answer.",
  collaboration:
    "Draws energy from working through people — teams, feedback, mentors.",
  executionTempo: "Moves quickly from decision to done — iteration over polish.",
};

export const traitLabels: Record<TraitKey, string> = {
  builder: "Builder",
  analyst: "Analyst",
  riskTolerance: "Risk tolerance",
  ambiguityComfort: "Ambiguity comfort",
  collaboration: "Collaboration",
  executionTempo: "Execution tempo",
};

/**
 * The bank: 20 questions, the two formats interleaved on purpose.
 *
 * Scenario picks force a tradeoff — choosing the hackathon is choosing *not*
 * to choose the research fair — which is what pulls the field percentages
 * apart instead of letting them cluster. Agreement statements measure each
 * trait on its own axis, which a forced pick cannot do: liking both building
 * and analysis is a real answer, and only the 1-5 items can record it.
 * Alternating them also breaks the rhythm that makes long quizzes get
 * straight-lined.
 */
export const assessmentQuestions: AssessmentQuestion[] = [
  {
    kind: "choice",
    id: "q1-free-afternoon",
    prompt: "You have one free afternoon. What do you choose?",
    choices: [
      {
        id: "build-project",
        label: "Build a small project and ship something tangible.",
        traits: { builder: 2, executionTempo: 1 },
      },
      {
        id: "research-topic",
        label: "Research a complicated topic until the pattern clicks.",
        traits: { analyst: 2, ambiguityComfort: 1 },
      },
      {
        id: "gather-team",
        label: "Pull a few friends together and test an idea as a group.",
        traits: { collaboration: 2, builder: 1 },
      },
      {
        id: "pitch-stranger",
        label: "Take a shot at something you might not get — an email, an application, a pitch.",
        traits: { riskTolerance: 2, executionTempo: 1 },
      },
      {
        id: "wander-unplanned",
        label: "Leave it unplanned and follow whatever turns out to be interesting.",
        traits: { ambiguityComfort: 2, riskTolerance: 1 },
      },
    ],
  },
  {
    kind: "likert",
    id: "l1-ship-rough",
    prompt:
      "I would rather ship something rough this week than spend a month making it perfect.",
    traits: { builder: 2, executionTempo: 2 },
  },
  {
    kind: "likert",
    id: "l2-understand-first",
    prompt:
      "Before I start building, I want to understand why the problem exists in the first place.",
    traits: { analyst: 2, ambiguityComfort: 1 },
  },
  {
    kind: "choice",
    id: "q2-competition-choice",
    prompt: "You can enter one competition. Which one sounds most energizing?",
    choices: [
      {
        id: "hackathon",
        label: "A weekend build-a-thon — any medium — where speed and demos matter.",
        traits: { builder: 2, executionTempo: 2, riskTolerance: 1 },
      },
      {
        id: "research-fair",
        label: "A research fair where depth and evidence matter.",
        traits: { analyst: 2, ambiguityComfort: 1 },
      },
      {
        id: "pitch-contest",
        label: "A pitch contest where persuasion and uncertainty matter.",
        traits: { riskTolerance: 2, collaboration: 1 },
      },
      {
        id: "team-relay",
        label: "A team event where your score is the whole group's score.",
        traits: { collaboration: 2, executionTempo: 1 },
      },
      {
        id: "open-problem",
        label: "A month-long open problem nobody has solved yet.",
        traits: { ambiguityComfort: 2, analyst: 2 },
      },
    ],
  },
  {
    kind: "likert",
    id: "l3-long-odds",
    prompt:
      "I would enter something I might lose if the payoff for winning were big enough.",
    traits: { riskTolerance: 3 },
  },
  {
    kind: "likert",
    id: "l4-need-instructions",
    prompt: "I need clear instructions before I feel comfortable starting.",
    traits: { ambiguityComfort: 3 },
    reverse: true,
  },
  {
    kind: "likert",
    id: "l5-think-out-loud",
    prompt: "I think best out loud, with other people in the room.",
    traits: { collaboration: 3 },
  },
  {
    kind: "likert",
    id: "l6-every-option",
    prompt: "I put off deciding until I have looked at every option.",
    traits: { executionTempo: 3 },
    reverse: true,
  },
  {
    kind: "choice",
    id: "q3-team-role",
    prompt: "On a team, the role you naturally drift toward is...",
    choices: [
      {
        id: "maker",
        label: "The maker who turns ideas into something usable.",
        traits: { builder: 2, executionTempo: 1 },
      },
      {
        id: "strategist",
        label: "The strategist who clarifies the problem and the evidence.",
        traits: { analyst: 2, ambiguityComfort: 1 },
      },
      {
        id: "connector",
        label: "The connector who keeps people aligned and moving.",
        traits: { collaboration: 2, executionTempo: 1 },
      },
      {
        id: "closer",
        label: "The closer who drags the last 10% over the line.",
        traits: { executionTempo: 2, builder: 1 },
      },
      {
        id: "wildcard",
        label: "The wildcard who keeps pushing the idea everyone else called too risky.",
        traits: { riskTolerance: 2, ambiguityComfort: 1 },
      },
    ],
  },
  // From here the questions lean on field signal. The picks force tradeoffs
  // between fields; the statements let a student rate an interest without
  // having to rank it against something unrelated.
  {
    kind: "choice",
    id: "q4-headline",
    prompt: "Which headline pulls you in first?",
    choices: [
      {
        id: "ai-diagnosis",
        label: "AI model beats doctors at spotting rare diseases.",
        traits: { analyst: 1 },
        fields: { cs: 2, biology: 1 },
      },
      {
        id: "black-hole",
        label: "New telescope catches a black hole forming in real time.",
        traits: { analyst: 1, ambiguityComfort: 1 },
        fields: { physics: 2, math: 1 },
      },
      {
        id: "student-investigation",
        label: "Student newspaper investigation gets a state law changed.",
        traits: { collaboration: 1, riskTolerance: 1 },
        fields: { humanities: 2, business: 1 },
      },
      {
        id: "lab-grown-organ",
        label: "Lab-grown organ keeps a patient alive for the first time.",
        traits: { analyst: 1, builder: 1 },
        fields: { health: 2, biology: 2 },
      },
      {
        id: "teen-founders",
        label: "Two teenagers turn a class project into a real company.",
        traits: { riskTolerance: 1, executionTempo: 1 },
        fields: { business: 2, design: 1 },
      },
    ],
  },
  {
    kind: "likert",
    id: "l7-proof-clicks",
    prompt: "A proof or a puzzle that finally clicks is deeply satisfying to me.",
    traits: { analyst: 1 },
    fields: { math: 3 },
  },
  {
    kind: "likert",
    id: "l8-disease-spread",
    prompt:
      "I would read about how a treatment works or how a disease spreads for fun.",
    traits: { analyst: 1 },
    fields: { health: 2, biology: 2 },
  },
  {
    kind: "likert",
    id: "l9-bad-design",
    prompt: "I notice when an app, sign, or poster is badly designed, and it bothers me.",
    traits: { builder: 1 },
    fields: { design: 3 },
  },
  {
    kind: "choice",
    id: "q5-fun-class",
    prompt: "Which hard class would you take just for fun?",
    choices: [
      {
        id: "number-theory",
        label: "Number theory: pure puzzles, no calculator allowed.",
        traits: { analyst: 1, ambiguityComfort: 1 },
        fields: { math: 2 },
      },
      {
        id: "quantum",
        label: "Quantum mechanics: reality is weirder than fiction.",
        traits: { ambiguityComfort: 1 },
        fields: { physics: 2, math: 1 },
      },
      {
        id: "bioengineering",
        label: "Bioengineering: grow materials instead of manufacturing them.",
        traits: { builder: 1 },
        fields: { biology: 2, engineering: 1 },
      },
      {
        id: "architecture-studio",
        label: "Architecture studio: design a building people would want to live in.",
        traits: { builder: 1, collaboration: 1 },
        fields: { design: 2, engineering: 1 },
      },
      {
        id: "ethics-of-tech",
        label: "Ethics of technology: who gets hurt when the thing actually ships.",
        traits: { analyst: 1, ambiguityComfort: 1 },
        fields: { humanities: 2, cs: 1 },
      },
    ],
  },
  {
    kind: "likert",
    id: "l10-argue-meaning",
    prompt:
      "I enjoy arguing about what a book, a film, or a piece of history actually meant.",
    traits: { ambiguityComfort: 1 },
    fields: { humanities: 3 },
  },
  {
    kind: "likert",
    id: "l11-why-it-worked",
    prompt:
      "Figuring out why a company or a product won is as interesting to me as the product itself.",
    traits: { analyst: 1 },
    fields: { business: 3 },
  },
  {
    kind: "likert",
    id: "l12-build-physical",
    prompt: "I want to build the physical thing, not just the plan for it.",
    traits: { builder: 2 },
    fields: { engineering: 3 },
  },
  {
    kind: "choice",
    id: "q6-career-day",
    prompt: "At career day, you corner which speaker with questions?",
    choices: [
      {
        id: "game-engineer",
        label: "The engineer who ships a game millions of people play.",
        traits: { builder: 1, executionTempo: 1 },
        fields: { cs: 2 },
      },
      {
        id: "climate-scientist",
        label: "The climate scientist working across five different fields.",
        traits: { collaboration: 1, ambiguityComfort: 1 },
        fields: { interdisciplinary: 2, physics: 1 },
      },
      {
        id: "dorm-founder",
        label: "The founder who bootstrapped a company from their dorm room.",
        traits: { riskTolerance: 1, executionTempo: 1 },
        fields: { business: 2 },
      },
      {
        id: "trauma-surgeon",
        label: "The trauma surgeon who decides faster than anyone you have met.",
        traits: { executionTempo: 1, riskTolerance: 1 },
        fields: { health: 2, biology: 1 },
      },
      {
        id: "documentary-director",
        label: "The director whose documentary changed how people saw something.",
        traits: { collaboration: 1, ambiguityComfort: 1 },
        fields: { humanities: 2, design: 1 },
      },
    ],
  },
  {
    kind: "likert",
    id: "l13-two-fields",
    prompt:
      "I would rather work on a problem that needs two different fields at once than one that stays in its lane.",
    traits: { ambiguityComfort: 1, collaboration: 1 },
    fields: { interdisciplinary: 3 },
  },
  {
    kind: "likert",
    id: "l14-what-universe-is",
    prompt:
      "What the universe is made of interests me more than most practical questions.",
    traits: { analyst: 1, ambiguityComfort: 1 },
    fields: { physics: 3 },
  },
];
