import type { TraitKey } from "./assessment";

export type Archetype = {
  id: string;
  label: string;
  summary: string;
  traits: Record<TraitKey, number>;
};

export const archetypes: Archetype[] = [
  {
    id: "applied-ai-builder",
    label: "Applied AI Builder",
    summary:
      "Builds practical AI tools, moves quickly from prototype to demo, and learns best by shipping.",
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
    traits: {
      builder: 7,
      analyst: 6,
      riskTolerance: 5,
      ambiguityComfort: 7,
      collaboration: 9,
      executionTempo: 6,
    },
  },
];
