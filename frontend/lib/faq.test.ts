import { describe, expect, it } from "vitest";
import { answerFromFaq } from "./faq";

describe("answerFromFaq", () => {
  it("answers the question that broke the advisor", () => {
    // Verbatim from a real session. The advisor replied "you do not have a
    // set map or plan provided in the sources" and recommended three summer
    // programmes, because the only corpus it has is matched opportunities.
    const got = answerFromFaq("i have a question; where do I see my map/plan?");
    expect(got?.id).toBe("plan");
    expect(got?.links[0].href).toBe("/plan");
  });

  it.each([
    ["where is my roadmap", "plan"],
    ["How do I retake the assessment?", "assessment"],
    ["where can i browse opportunities", "matches"],
    ["what is northstar", "what"],
    ["is this free?", "cost"],
    ["how do i delete my account", "profile"],
    ["where do i find free textbooks", "learn"],
    ["how can I find other students", "people"],
    ["why is this ranked first", "ranking"],
    ["is this just an AI chatbot", "ai"],
  ])("%s -> %s", (question, id) => {
    expect(answerFromFaq(question)?.id).toBe(id);
  });

  it("does NOT intercept the questions the advisor exists for", () => {
    // A false positive here is worse than a miss: it would answer a question
    // about the student's future with a link to a settings page.
    const exploration = [
      "What unusual routes fit how I actually think?",
      "How could I combine my top two fields into one direction?",
      "What would a non-obvious college major look like for me?",
      "I like debate and biology, what routes combine them?",
      "Should I focus on competitions or research first",
      "Tell me about quantum computing",
    ];
    for (const question of exploration) {
      expect(answerFromFaq(question), question).toBeNull();
    }
  });

  it("needs an intent cue, not just a topic word", () => {
    // Bare nouns are a research prompt, not a navigation question.
    expect(answerFromFaq("plan")).toBeNull();
    expect(answerFromFaq("opportunities in robotics")).toBeNull();
    expect(answerFromFaq("my profile as a builder suggests")).toBeNull();
  });

  it("is quiet on junk rather than guessing", () => {
    for (const junk of ["", "  ", "?", "ok"]) {
      expect(answerFromFaq(junk)).toBeNull();
    }
  });
});
