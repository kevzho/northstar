import type { TraitKey } from "./assessment";
import type { OpportunityField } from "./types";

export type Archetype = {
  id: string;
  label: string;
  summary: string;
  /** The opportunity fields this profession lives closest to — used to
   * nudge rankings toward a signed-in student's stated interests. */
  fields: OpportunityField[];
  traits: Record<TraitKey, number>;
};

/**
 * Twelve professions spanning all six opportunity fields — builders,
 * researchers, communicators, and field scientists, not just software
 * shapes. Trait vectors are hand-set on a 0–10 scale; they are the other
 * half of the cosine match in lib/scoring.ts.
 */
export const archetypes: Archetype[] = [
  {
    id: "applied-ai-builder",
    label: "Applied AI Builder",
    summary:
      "Builds practical AI tools, moves quickly from prototype to demo, and learns best by shipping.",
    fields: ["cs"],
    traits: {
      builder: 9,
      analyst: 7,
      riskTolerance: 6,
      ambiguityComfort: 7,
      collaboration: 5,
      executionTempo: 8,
    },
  },
  {
    id: "computational-biology-researcher",
    label: "Computational Biology Researcher",
    summary:
      "Uses code, statistics, and patient investigation to understand complex biological systems.",
    fields: ["biology", "cs"],
    traits: {
      builder: 5,
      analyst: 9,
      riskTolerance: 4,
      ambiguityComfort: 8,
      collaboration: 6,
      executionTempo: 5,
    },
  },
  {
    id: "technical-founder",
    label: "Technical Founder",
    summary:
      "Turns unclear problems into products, accepts uncertainty, and recruits others into the mission.",
    fields: ["cs", "interdisciplinary"],
    traits: {
      builder: 9,
      analyst: 6,
      riskTolerance: 9,
      ambiguityComfort: 8,
      collaboration: 8,
      executionTempo: 9,
    },
  },
  {
    id: "product-minded-engineer",
    label: "Product-Minded Engineer",
    summary:
      "Balances technical execution with user needs, feedback loops, and thoughtful prioritization.",
    fields: ["cs", "engineering"],
    traits: {
      builder: 8,
      analyst: 7,
      riskTolerance: 5,
      ambiguityComfort: 6,
      collaboration: 8,
      executionTempo: 7,
    },
  },
  {
    id: "civic-technology-designer",
    label: "Civic Technology Designer",
    summary:
      "Builds tools for public benefit, working closely with communities and real-world constraints.",
    fields: ["interdisciplinary"],
    traits: {
      builder: 7,
      analyst: 6,
      riskTolerance: 5,
      ambiguityComfort: 7,
      collaboration: 9,
      executionTempo: 6,
    },
  },
  {
    id: "research-mathematician",
    label: "Research Mathematician",
    summary:
      "Chases abstract structure for its own sake — long problems, deep focus, and proofs that either hold or don't.",
    fields: ["math"],
    traits: {
      builder: 3,
      analyst: 10,
      riskTolerance: 4,
      ambiguityComfort: 9,
      collaboration: 4,
      executionTempo: 3,
    },
  },
  {
    id: "experimental-physicist",
    label: "Experimental Physicist",
    summary:
      "Designs experiments that force nature to answer — half theory, half building the apparatus that tests it.",
    fields: ["physics", "engineering"],
    traits: {
      builder: 6,
      analyst: 8,
      riskTolerance: 5,
      ambiguityComfort: 7,
      collaboration: 6,
      executionTempo: 5,
    },
  },
  {
    id: "robotics-engineer",
    label: "Robotics Engineer",
    summary:
      "Makes machines that move in the physical world, where every bug is visible and iteration is hands-on.",
    fields: ["engineering", "cs"],
    traits: {
      builder: 9,
      analyst: 6,
      riskTolerance: 5,
      ambiguityComfort: 5,
      collaboration: 7,
      executionTempo: 7,
    },
  },
  {
    id: "biomedical-innovator",
    label: "Biomedical Innovator",
    summary:
      "Works at the seam of medicine and engineering — devices, diagnostics, and therapies that reach real patients.",
    fields: ["biology", "engineering"],
    traits: {
      builder: 7,
      analyst: 7,
      riskTolerance: 6,
      ambiguityComfort: 6,
      collaboration: 7,
      executionTempo: 6,
    },
  },
  {
    id: "data-scientist",
    label: "Data Scientist",
    summary:
      "Finds the signal in messy real-world data and turns it into decisions people actually make.",
    fields: ["math", "cs"],
    traits: {
      builder: 6,
      analyst: 9,
      riskTolerance: 4,
      ambiguityComfort: 6,
      collaboration: 6,
      executionTempo: 6,
    },
  },
  {
    id: "science-communicator",
    label: "Science Communicator",
    summary:
      "Translates hard ideas for real audiences — writing, teaching, and building the bridge between labs and everyone else.",
    fields: ["interdisciplinary"],
    traits: {
      builder: 5,
      analyst: 6,
      riskTolerance: 6,
      ambiguityComfort: 7,
      collaboration: 9,
      executionTempo: 7,
    },
  },
  {
    id: "field-research-scientist",
    label: "Field Research Scientist",
    summary:
      "Collects data where it lives — ecosystems, oceans, atmospheres — and works patiently through uncontrolled conditions.",
    fields: ["biology", "physics"],
    traits: {
      builder: 4,
      analyst: 7,
      riskTolerance: 6,
      ambiguityComfort: 8,
      collaboration: 5,
      executionTempo: 4,
    },
  },
  // --- Expansion wave: design, business, humanities, health, hybrids ---
  {
    id: "game-designer",
    label: "Game Designer",
    summary:
      "Designs systems people want to live inside — rules, feedback, and feel — and playtests relentlessly until it clicks.",
    fields: ["design", "cs"],
    traits: {
      builder: 8,
      analyst: 6,
      riskTolerance: 6,
      ambiguityComfort: 7,
      collaboration: 6,
      executionTempo: 7,
    },
  },
  {
    id: "product-designer",
    label: "Product Designer",
    summary:
      "Makes complicated things feel obvious. Lives in the gap between what people say they want and what they actually do.",
    fields: ["design"],
    traits: {
      builder: 7,
      analyst: 7,
      riskTolerance: 4,
      ambiguityComfort: 7,
      collaboration: 8,
      executionTempo: 6,
    },
  },
  {
    id: "digital-media-artist",
    label: "Digital Media Artist",
    summary:
      "Ships creative work in public on a steady cadence — video, image, sound — and treats the audience as a collaborator.",
    fields: ["design", "humanities"],
    traits: {
      builder: 8,
      analyst: 4,
      riskTolerance: 7,
      ambiguityComfort: 8,
      collaboration: 5,
      executionTempo: 8,
    },
  },
  {
    id: "social-entrepreneur",
    label: "Social Entrepreneur",
    summary:
      "Builds ventures where the unit economics and the mission have to work at the same time — and tests both with real people early.",
    fields: ["business", "interdisciplinary"],
    traits: {
      builder: 7,
      analyst: 6,
      riskTolerance: 8,
      ambiguityComfort: 7,
      collaboration: 8,
      executionTempo: 7,
    },
  },
  {
    id: "quantitative-economist",
    label: "Quantitative Economist",
    summary:
      "Reads the world as incentives and tradeoffs, and settles arguments with data instead of vibes.",
    fields: ["business", "math"],
    traits: {
      builder: 4,
      analyst: 9,
      riskTolerance: 5,
      ambiguityComfort: 7,
      collaboration: 5,
      executionTempo: 5,
    },
  },
  {
    id: "investigative-journalist",
    label: "Investigative Journalist",
    summary:
      "Chases the documented truth: records requests, source interviews, and the patience to be right instead of first.",
    fields: ["humanities", "interdisciplinary"],
    traits: {
      builder: 5,
      analyst: 8,
      riskTolerance: 8,
      ambiguityComfort: 8,
      collaboration: 7,
      executionTempo: 6,
    },
  },
  {
    id: "science-policy-advocate",
    label: "Science Policy Advocate",
    summary:
      "Translates evidence into decisions — briefs, hearings, and the unglamorous work of making institutions move.",
    fields: ["humanities", "health"],
    traits: {
      builder: 4,
      analyst: 8,
      riskTolerance: 6,
      ambiguityComfort: 8,
      collaboration: 9,
      executionTempo: 5,
    },
  },
  {
    id: "public-health-strategist",
    label: "Public Health Strategist",
    summary:
      "Improves health at the scale of populations — measuring behaviors, designing nudges, and caring about who gets left out.",
    fields: ["health", "interdisciplinary"],
    traits: {
      builder: 5,
      analyst: 8,
      riskTolerance: 5,
      ambiguityComfort: 7,
      collaboration: 8,
      executionTempo: 6,
    },
  },
  {
    id: "sports-scientist",
    label: "Sports Scientist",
    summary:
      "Treats performance as an experiment: measure, tweak, measure again — on real athletes, starting with yourself.",
    fields: ["health", "engineering"],
    traits: {
      builder: 7,
      analyst: 8,
      riskTolerance: 5,
      ambiguityComfort: 5,
      collaboration: 7,
      executionTempo: 8,
    },
  },
  {
    id: "bioethicist",
    label: "Bioethicist",
    summary:
      "Sits where biology outruns the rulebook and reasons carefully in public about what we should do next.",
    fields: ["humanities", "biology"],
    traits: {
      builder: 3,
      analyst: 9,
      riskTolerance: 5,
      ambiguityComfort: 9,
      collaboration: 7,
      executionTempo: 4,
    },
  },
  {
    id: "edtech-creator",
    label: "EdTech Creator",
    summary:
      "Builds the explainer they wish they'd had, measures whether it actually teaches, and iterates like a scientist.",
    fields: ["design", "business"],
    traits: {
      builder: 8,
      analyst: 6,
      riskTolerance: 6,
      ambiguityComfort: 6,
      collaboration: 7,
      executionTempo: 7,
    },
  },
  {
    id: "conservation-storyteller",
    label: "Conservation Storyteller",
    summary:
      "Pairs field data with narrative craft so the places worth saving get argued for, not just mourned.",
    fields: ["humanities", "biology"],
    traits: {
      builder: 6,
      analyst: 6,
      riskTolerance: 6,
      ambiguityComfort: 8,
      collaboration: 6,
      executionTempo: 5,
    },
  },
];
