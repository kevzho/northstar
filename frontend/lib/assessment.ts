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

export type AssessmentChoice = {
  id: string;
  label: string;
  traits: TraitDeltas;
  /** Field-interest weights; only the field-signal questions carry these. */
  fields?: FieldDeltas;
};

export type AssessmentQuestion = {
  id: string;
  prompt: string;
  choices: AssessmentChoice[];
};

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

export const assessmentQuestions: AssessmentQuestion[] = [
  {
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
    ],
  },
  {
    id: "q2-unclear-assignment",
    prompt: "A teacher gives you an open-ended project with few rules. You...",
    choices: [
      {
        id: "define-scope",
        label: "Define a clear scope, make milestones, and start building.",
        traits: { builder: 1, executionTempo: 2 },
      },
      {
        id: "explore-angles",
        label: "Explore several possible angles before choosing a direction.",
        traits: { analyst: 1, ambiguityComfort: 2 },
      },
      {
        id: "ask-feedback",
        label: "Talk through early ideas with classmates and mentors.",
        traits: { collaboration: 2, ambiguityComfort: 1 },
      },
    ],
  },
  {
    id: "q3-competition-choice",
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
    ],
  },
  {
    id: "q4-stuck-moment",
    prompt: "You get stuck on a hard problem. Your first move is to...",
    choices: [
      {
        id: "debug-alone",
        label: "Break it into smaller pieces and debug by yourself.",
        traits: { analyst: 2, executionTempo: 1 },
      },
      {
        id: "prototype-around",
        label: "Try a rough workaround so the project keeps moving.",
        traits: { builder: 2, riskTolerance: 1 },
      },
      {
        id: "find-helper",
        label: "Ask someone sharper in that area and compare approaches.",
        traits: { collaboration: 2, ambiguityComfort: 1 },
      },
    ],
  },
  {
    id: "q5-summer-plan",
    prompt: "You are choosing a summer focus. You would rather...",
    choices: [
      {
        id: "launch-app",
        label: "Launch something real — an app, a zine, a small business — even if v1 is rough.",
        traits: { builder: 2, riskTolerance: 2, executionTempo: 1 },
      },
      {
        id: "deep-study",
        label: "Study a demanding field and produce a serious writeup.",
        traits: { analyst: 2, ambiguityComfort: 1 },
      },
      {
        id: "community-program",
        label: "Run a small program that helps people in your community.",
        traits: { collaboration: 2, builder: 1 },
      },
    ],
  },
  {
    id: "q6-feedback",
    prompt: "When someone critiques your work, you usually...",
    choices: [
      {
        id: "revise-fast",
        label: "Revise quickly and test whether the change improves it.",
        traits: { executionTempo: 2, builder: 1 },
      },
      {
        id: "inspect-logic",
        label: "Inspect the logic behind the critique before changing direction.",
        traits: { analyst: 2, ambiguityComfort: 1 },
      },
      {
        id: "discuss-tradeoffs",
        label: "Discuss tradeoffs so everyone agrees on the next version.",
        traits: { collaboration: 2, ambiguityComfort: 1 },
      },
    ],
  },
  {
    id: "q7-risk",
    prompt: "A risky opportunity appears, but the upside is meaningful. You...",
    choices: [
      {
        id: "take-shot",
        label: "Take the shot and learn from the result.",
        traits: { riskTolerance: 2, executionTempo: 1 },
      },
      {
        id: "model-outcomes",
        label: "Model the downside, upside, and decision criteria first.",
        traits: { analyst: 2, riskTolerance: 1 },
      },
      {
        id: "pilot-small",
        label: "Run a small pilot with collaborators before committing.",
        traits: { collaboration: 1, builder: 1, ambiguityComfort: 1 },
      },
    ],
  },
  {
    id: "q8-team-role",
    prompt: "On a team, the role you naturally drift toward is...",
    choices: [
      {
        id: "maker",
        label: "The maker who turns ideas into something usable.",
        traits: { builder: 2, executionTempo: 1 },
      },
      {
        id: "strategist",
        label: "The strategist who clarifies the problem and evidence.",
        traits: { analyst: 2, ambiguityComfort: 1 },
      },
      {
        id: "connector",
        label: "The connector who keeps people aligned and moving.",
        traits: { collaboration: 2, executionTempo: 1 },
      },
    ],
  },
  // Questions 9-14 are field-signal prompts: they still carry light trait
  // deltas, but their main job is forcing tradeoffs between fields so the
  // interest percentages come out distinct instead of uniformly mild.
  {
    id: "q9-headline",
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
    ],
  },
  {
    id: "q10-exhibit",
    prompt: "Free ticket to one museum exhibit. You pick...",
    choices: [
      {
        id: "gene-lab",
        label: "The genetics lab: edit DNA in a dish and watch what happens.",
        traits: { analyst: 1 },
        fields: { biology: 2 },
      },
      {
        id: "trading-floor",
        label: "The trading floor: run a mock market against real strategies.",
        traits: { analyst: 1, riskTolerance: 1 },
        fields: { business: 2, math: 1 },
      },
      {
        id: "maker-floor",
        label: "The maker floor: motors, circuits, and 3D printers running.",
        traits: { builder: 1, executionTempo: 1 },
        fields: { engineering: 2, cs: 1 },
      },
    ],
  },
  {
    id: "q11-series",
    prompt: "You would actually binge a series about...",
    choices: [
      {
        id: "how-internet-works",
        label: "How the internet really works, from wires to protocols.",
        traits: { analyst: 1 },
        fields: { cs: 2 },
      },
      {
        id: "outbreak",
        label: "How outbreaks start, spread, and get stopped.",
        traits: { ambiguityComfort: 1, collaboration: 1 },
        fields: { biology: 2, health: 1 },
      },
      {
        id: "design-icons",
        label: "Why the best-designed things feel obvious — and the rest don't.",
        traits: { builder: 1 },
        fields: { design: 2, engineering: 1 },
      },
    ],
  },
  {
    id: "q12-weekend-pitch",
    prompt: "A friend pitches a weekend project. Which pitch wins?",
    choices: [
      {
        id: "game-bot",
        label: "Train a bot to beat us at our favorite game.",
        traits: { builder: 1 },
        fields: { cs: 2, math: 1 },
      },
      {
        id: "model-rocket",
        label: "Build and launch a model rocket from scratch.",
        traits: { builder: 1, riskTolerance: 1 },
        fields: { engineering: 2, physics: 1 },
      },
      {
        id: "wellness-week",
        label: "Organize a mental-health awareness week people actually attend.",
        traits: { collaboration: 1 },
        fields: { health: 2, interdisciplinary: 1 },
      },
    ],
  },
  {
    id: "q13-fun-class",
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
    ],
  },
  {
    id: "q14-career-day",
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
    ],
  },
  {
    id: "q15-free-elective",
    prompt: "You get one free elective, no requirements. You pick...",
    choices: [
      {
        id: "studio-design",
        label: "Studio art and digital design — make things that look right.",
        traits: { builder: 1 },
        fields: { design: 2 },
      },
      {
        id: "entrepreneurship",
        label: "Entrepreneurship — turn an idea into something people want.",
        traits: { riskTolerance: 1 },
        fields: { business: 2 },
      },
      {
        id: "global-health",
        label: "Global health — why some communities thrive and others do not.",
        traits: { ambiguityComfort: 1 },
        fields: { health: 2, interdisciplinary: 1 },
      },
    ],
  },
  {
    id: "q16-dream-project",
    prompt: "Your dream school project would be...",
    choices: [
      {
        id: "short-documentary",
        label: "Directing a short documentary about something overlooked.",
        traits: { collaboration: 1 },
        fields: { humanities: 2, design: 1 },
      },
      {
        id: "assistive-device",
        label: "Engineering an assistive device for a classmate who needs one.",
        traits: { builder: 1, collaboration: 1 },
        fields: { engineering: 2, health: 1 },
      },
      {
        id: "redesign-site",
        label: "Redesigning the school's confusing website so it makes sense.",
        traits: { builder: 1 },
        fields: { design: 2, cs: 1 },
      },
    ],
  },
  {
    id: "q17-news-first",
    prompt: "Which section of the news do you actually read first?",
    choices: [
      {
        id: "culture-essays",
        label: "Culture, essays, and opinion — the arguments.",
        traits: { ambiguityComfort: 1 },
        fields: { humanities: 2 },
      },
      {
        id: "markets-startups",
        label: "Markets and startups — who is building and who is winning.",
        traits: { analyst: 1 },
        fields: { business: 2 },
      },
      {
        id: "health-medicine",
        label: "Health and medicine — what actually helps people live better.",
        traits: { analyst: 1 },
        fields: { health: 2, biology: 1 },
      },
    ],
  },
];
