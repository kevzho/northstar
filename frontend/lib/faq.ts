/**
 * Questions about the product, answered without asking a model.
 *
 * WHY THIS EXISTS. The advisor is retrieval over one corpus: the student's own
 * profile and their verified matched opportunities. Asked "where do I see my
 * map?" it did the only thing it could and answered from that corpus -- "you
 * do not have a set map or plan provided in the sources" -- then recommended
 * three summer programmes. Every part of that is working as designed and the
 * whole of it is wrong, because the question was about the website.
 *
 * So navigation and product questions are answered from here instead: written
 * by hand, instant, free, no allowance spent, and incapable of inventing an
 * opportunity. The model is left for the thing it is actually good at.
 *
 * MATCHING IS DELIBERATELY STRICT. A false positive is worse than a miss: it
 * would intercept "what unusual routes fit how I think?" -- the question the
 * advisor exists for -- and answer it with a link to a settings page. So an
 * entry fires only when the question carries BOTH an intent cue (where, how do
 * I, what is, can I) AND one of that entry's own topic words. Anything else
 * falls through to the model untouched.
 */

export type FaqAnswer = {
  id: string;
  answer: string;
  links: { href: string; label: string }[];
};

/** "where", "how do I", "what is" -- a question about the thing, not the field. */
const INTENT =
  /\b(where|how (do|can|would) i|how to|what (is|are|does|'s)|whats|can i|could i|is (there|this|it)|do i (need|have to)|why (does|is|am i)|show me)\b/i;

type Entry = {
  id: string;
  /** Any one of these, plus an intent cue, fires the entry. */
  topics: RegExp;
  answer: string;
  links: { href: string; label: string }[];
};

const ENTRIES: Entry[] = [
  {
    id: "plan",
    topics: /\b(my )?(plan|roadmap|map|route|path|next step|steps?)\b/i,
    answer:
      "Your plan lives on the Plan page. It sequences what to learn, build, publish and apply to, in that order, and the diagram at the top is the same plan drawn as a route. Click any node on it to break that step into the smaller moves inside it, or ask for other directions out of the same step.",
    links: [{ href: "/plan", label: "Open your plan" }],
  },
  {
    id: "matches",
    topics: /\b(match(es|ed)?|opportunit(y|ies)|programs?|programmes?|internships?|scholarships?|competitions?|catalog(ue)?|browse)\b/i,
    answer:
      "Browse the catalog on the Opportunities page. Every row is a real programme someone checked, with its deadline and whether you can simply apply or need a teacher nomination or a qualifying round first. Each match carries the reason it was ranked for you.",
    links: [{ href: "/opportunities", label: "Browse opportunities" }],
  },
  {
    id: "assessment",
    topics: /\b(assessment|quiz|questions?|retake|redo|traits?|profile test)\b/i,
    answer:
      "The assessment is twenty questions and scores six traits: Builder, Analyst, Risk tolerance, Ambiguity comfort, Collaboration and Execution tempo. You can retake it whenever you like, and the new answers replace the old profile.",
    links: [
      { href: "/assessment", label: "Take or retake it" },
      { href: "/profile", label: "See your profile" },
    ],
  },
  {
    id: "ranking",
    topics: /\b(rank(ed|ing)?|score[ds]?|why (this|that|am i)|recommend(ed|ation)?|algorithm|how.*(chosen|picked|sorted))\b/i,
    answer:
      "Matching is deterministic, not a model. Your profile is scored against the catalog by term overlap, with a semantic retrieval supplement, and every result shows the reason it matched: the field, the grade window, the tag. No language model decides what ranks where, which is why each match can tell you why it is there.",
    links: [{ href: "/opportunities", label: "See your matches" }],
  },
  {
    id: "learn",
    topics: /\b(learn|resources?|textbooks?|courses?|study|free (books?|pdfs?))\b/i,
    answer:
      "The Learn shelf holds free textbooks and courses, including OpenStax. Everything on it links to a page that was opened and read, and free means free to the student, with the sentence that proves it.",
    links: [{ href: "/learn", label: "Open the Learn shelf" }],
  },
  {
    id: "people",
    topics: /\b(friends?|people|peers?|team ?up|collaborat(e|ors?)|partners?|others?|classmates)\b/i,
    answer:
      "Find students on the same path from the People pages. You can compare paths with someone you have added, or signal that you are open to teaming up on a project.",
    links: [
      { href: "/friends", label: "Find your people" },
      { href: "/teamup", label: "Team up" },
    ],
  },
  {
    id: "profile",
    topics: /\b(profile|account|settings|edit|change my|handle|username|delete|sign out|log out)\b/i,
    answer:
      "Your profile page holds your details, your handle and your public page. Deleting your account is there too, and it removes your rows rather than hiding them.",
    links: [{ href: "/profile", label: "Open your profile" }],
  },
  {
    id: "what",
    topics: /\b(northstar|this (app|site|tool|thing)|the app|what.*(do|for))\b/i,
    answer:
      "Northstar is a catalog of real STEM opportunities for high schoolers, plus a plan telling you what to learn, build and publish before an application is worth sending. It is free, it needs no school login, and applications come last on purpose.",
    links: [
      { href: "/dashboard", label: "Dashboard" },
      { href: "/faq", label: "Full FAQ" },
    ],
  },
  {
    id: "cost",
    topics: /\b(free|cost|pay|paid|price|money|subscription|charge)\b/i,
    answer:
      "Northstar is free and there is nothing to buy. Almost everything in the catalog is also free to apply to; the handful that charge say so on the card, and a programme being free to apply to does not always mean free to attend.",
    links: [{ href: "/opportunities", label: "Browse opportunities" }],
  },
  {
    id: "ai",
    topics: /\b(ai|a\.i\.|model|llm|chatbot|gpt|generated?|hallucinat)/i,
    answer:
      "A language model writes prose and helps screen scraped candidates. It never ranks anything, never invents a programme or a deadline, and anything it writes into your plan is checked first: no links we have not opened, no programmes we cannot verify. The ranking engine is deterministic.",
    links: [{ href: "/faq", label: "Full FAQ" }],
  },
];

/**
 * A product answer, or null to let the model handle it.
 *
 * Returns the FIRST entry whose topic matches, so order in ENTRIES is
 * precedence: "where is my plan" should answer about the plan even though it
 * also contains a word the ranking entry watches for.
 */
export function answerFromFaq(question: string): FaqAnswer | null {
  const text = (question || "").trim();
  if (text.length < 3) return null;
  if (!INTENT.test(text)) return null;
  for (const entry of ENTRIES) {
    if (entry.topics.test(text)) {
      return { id: entry.id, answer: entry.answer, links: entry.links };
    }
  }
  return null;
}
