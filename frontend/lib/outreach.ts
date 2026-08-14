/**
 * Mentor outreach drafts — a cold email the student edits, not a form letter
 * the student sends blind.
 *
 * The draft is a pure function of the student profile and the mentor card:
 * it names the overlap between the student's interests and the mentor's
 * expertise (that overlap is *why* the matcher ranked this mentor), asks one
 * concrete question, and stays under 150 words — short enough that a busy
 * adult actually reads it. Bracketed [EDIT] markers show exactly where the
 * student must make it their own before sending.
 */

import type { MentorMatch } from "./api";
import type { StudentProfile } from "./types";

export type EmailDraft = {
  subject: string;
  body: string;
};

function overlap(interests: string[], expertise: string[]): string[] {
  const expertiseLower = expertise.map((item) => item.toLowerCase());
  return interests.filter((interest) =>
    expertiseLower.some(
      (item) =>
        item.includes(interest.toLowerCase()) ||
        interest.toLowerCase().includes(item),
    ),
  );
}

export function buildIntroEmail(
  match: MentorMatch,
  profile: StudentProfile | null,
): EmailDraft {
  const { mentor } = match;
  const name = profile?.name?.trim() || "[EDIT: your name]";
  const grade = profile?.grade ? `a grade ${profile.grade} student` : "a high school student";
  const interests = profile?.interests ?? [];
  const goals = profile?.goals?.trim();

  const shared = overlap(interests, mentor.expertise);
  const sharedLine =
    shared.length > 0
      ? `I'm especially interested in ${shared.join(" and ").toLowerCase()}, which is why your background stood out to me.`
      : `Your background in ${mentor.expertise.slice(0, 2).join(" and ").toLowerCase()} stood out to me.`;

  const goalLine = goals
    ? `Right now my goal is: ${goals}`
    : "[EDIT: one sentence on what you're working toward.]";

  const subject = `Question from ${grade}${shared.length > 0 ? ` interested in ${shared[0].toLowerCase()}` : ""}`;

  const body = [
    `Hi ${mentor.name.split(" ")[0]},`,
    "",
    `I'm ${name}, ${grade}. I found you through Northstar, a STEM opportunity map that matched us based on my profile. ${sharedLine}`,
    "",
    goalLine,
    "",
    "[EDIT: one specific question you want to ask — specific beats general. \"How did you choose between X and Y\" beats \"any advice?\"]",
    "",
    "I know your time is limited — even a two-line reply would mean a lot.",
    "",
    `Thank you,`,
    name,
  ].join("\n");

  return { subject, body };
}

export function mailtoHref(email: string, draft: EmailDraft): string {
  return `mailto:${email}?subject=${encodeURIComponent(draft.subject)}&body=${encodeURIComponent(draft.body)}`;
}
