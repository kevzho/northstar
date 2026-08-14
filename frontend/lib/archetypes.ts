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
];
