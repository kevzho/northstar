import type { TraitKey } from "./assessment";
import type { OpportunityField } from "./types";

export type Archetype = {
  id: string;
  label: string;
  summary: string;
  /**
   * Concrete things a person on this path has actually done.
   *
   * The summary is a description of a profession, and a 15-year-old cannot
   * picture "quantitative economist" — they can picture "worked out whether a
   * bus route change really cut commute times". These are what make a path
   * tangible enough to accept or reject, which is the whole decision the
   * futures page asks for.
   */
  examples: string[];
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
    examples: [
      "Built a tool that summarises their class notes and actually uses it",
      "Fine-tuned a small model to sort their photos",
      "Shipped a Discord bot their friends still use",
    ],
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
    examples: [
      "Reproduced a figure from a published genetics paper with their own code",
      "Mapped which genes switch on in a public cancer dataset",
      "Wrote a script to align DNA sequences and found an error in the tutorial",
    ],
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
    examples: [
      "Charged five people for something they built in a weekend",
      "Ran a pre-order page before writing any code",
      "Rebuilt a product twice after watching someone fail to use it",
    ],
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
    examples: [
      "Rewrote an app's signup after watching three people get stuck",
      "Cut a feature that tested badly even though it took weeks",
      "Shipped the boring version first on purpose",
    ],
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
    examples: [
      "Made their city's bus data readable on a phone",
      "Built a form that helped neighbours apply for a grant",
      "Turned a council PDF into something searchable",
    ],
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
    examples: [
      "Proved a small result nobody asked them to prove",
      "Found a counterexample that broke their own conjecture",
      "Spent a month on one problem and enjoyed it",
    ],
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
    examples: [
      "Measured gravity with a phone and a piece of string, then argued about the error bars",
      "Built a cloud chamber from a fish tank",
      "Calibrated an instrument until the noise made sense",
    ],
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
    examples: [
      "Built an arm that fails gracefully instead of flailing",
      "Tuned a PID loop until the oscillation stopped",
      "Designed a gripper for one specific awkward object",
    ],
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
    examples: [
      "Prototyped a cheaper version of a clinic device",
      "Interviewed nurses before designing anything",
      "Read the FDA pathway before building the thing",
    ],
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
    examples: [
      "Found the confounder that explained an 'obvious' result",
      "Built a dashboard someone checks every Monday",
      "Threw out a model because the data was leaking",
    ],
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
    examples: [
      "Explained CRISPR to a room of twelve-year-olds and held them",
      "Wrote the thread that made a paper make sense",
      "Made a video that got the caveats right",
    ],
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
    examples: [
      "Counted the same stretch of river every week for a season",
      "Tagged bats and learned to hold still",
      "Kept a field notebook nobody made them keep",
    ],
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
    examples: [
      "Playtested a board game twenty times and cut half the rules",
      "Built a level that teaches without a tutorial",
      "Shipped a jam game in 48 hours",
    ],
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
    examples: [
      "Redrew a checkout until the drop-off stopped",
      "Ran a critique and changed their mind",
      "Designed for the slowest phone in the room",
    ],
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
    examples: [
      "Made a generative piece that surprised them",
      "Animated a concept their teacher could not explain",
      "Built a tool to make their own art faster",
    ],
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
    examples: [
      "Ran a food drive and tracked where it actually went",
      "Worked out the unit cost before scaling",
      "Shut down a programme that was not working",
    ],
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
    examples: [
      "Worked out whether a bus route change really cut commute times",
      "Found that a 'successful' policy was mostly seasonality",
      "Modelled their school's lunch queue",
    ],
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
    examples: [
      "Filed a records request and read the whole response",
      "Found the discrepancy between two public datasets",
      "Checked a claim everyone was repeating",
    ],
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
    examples: [
      "Read an actual bill and summarised what it would do",
      "Testified at a school board meeting",
      "Translated a study for someone who had to decide",
    ],
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
    examples: [
      "Mapped where the nearest clinic actually is by bus",
      "Worked out a rate per hundred thousand instead of a raw count",
      "Asked who was missing from the data",
    ],
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
    examples: [
      "Measured whether a warm-up routine changed anything",
      "Tracked sleep against performance for a season",
      "Learned why their first measurement was invalid",
    ],
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
    examples: [
      "Argued both sides of a gene-editing case and meant it",
      "Mapped who bears the risk and who gets the benefit",
      "Found the assumption buried in a consent form",
    ],
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
    examples: [
      "Built a practice tool and watched someone fail with it",
      "Tested whether their explanation actually taught",
      "Learned why spaced repetition works before building it",
    ],
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
    examples: [
      "Photographed one declining species for a year",
      "Made a map that changed how people voted locally",
      "Got the ecology right and the story readable",
    ],
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
