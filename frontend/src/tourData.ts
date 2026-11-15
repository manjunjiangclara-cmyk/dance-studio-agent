export type TourScenario = "booking" | "document";
export const tourSteps = [
  "Email",
  "Evidence",
  "Teacher review",
  "Confirmation",
] as const;

const clothingQuote =
  "Wear comfortable clothes you can move in, such as leggings and a fitted T-shirt. Socks are suitable for your first class; ballet shoes are optional.";
const sourceText = `Merri Ballet — Beginner clothing policy\n\nFor adult beginners attending a first class:\n${clothingQuote}\n\nBring water and tie long hair back. This document does not specify trial fees.\n`;

interface TourFixture {
  student: string;
  messages: { sender: string; body: string }[];
  evidence: string[];
  draft: string;
}
export const tourFixtures: Record<TourScenario, TourFixture> = {
  booking: {
    student: "Alex Morgan",
    messages: [
      {
        sender: "Alex Morgan · Original email",
        body: "I cannot attend Monday 8 February. Could I come Thursday instead?",
      },
      {
        sender: "Alex Morgan · Follow-up",
        body: "Actually, Saturday 13 February would be better.",
      },
    ],
    evidence: [
      "The latest email replaces Thursday with Saturday; the earlier preference is retained in the conversation history.",
      "The fictional absence notice arrived before Monday's session started.",
      "Recorded Level 2 attendance supports a Level 2 replacement under the example policy.",
      "Saturday 13 February 2027, 6 pm · Adult Ballet Level 2 · Brunswick. The fixture has one available place. No place is reserved before approval.",
    ],
    draft:
      "Hi Alex, thanks for letting me know. I've booked Saturday 13 February at 6 pm at our Brunswick studio for you. See you then!\n\nMerri Ballet team",
  },
  document: {
    student: "Jules Park",
    messages: [
      {
        sender: "Jules Park",
        body: "I'm new to ballet. What should I wear for my first class, and what does a trial cost?",
      },
    ],
    evidence: [
      "An explicitly enabled fictional clothing policy supplies the first-class clothing guidance.",
      "The exact supporting passage is available below. A citation identifies its saved revision; it does not prove every possible claim.",
      "No trial fee is specified in the selected source. The teacher must supply that fact or choose to confirm later.",
    ],
    draft:
      "Hi Jules, welcome! Wear comfortable clothes you can move in, such as leggings and a fitted T-shirt. Socks are suitable for your first class; ballet shoes are optional.\n\n[Teacher decision needed: trial fee]\n\nMerri Ballet team",
  },
};
export const tourSource = {
  title: "Beginner clothing policy",
  revision: 1,
  text: sourceText,
  quote: clothingQuote,
  start: sourceText.indexOf(clothingQuote),
  end: sourceText.indexOf(clothingQuote) + clothingQuote.length,
};
export function documentDraft(
  decision: "answer" | "defer",
  answer: string,
  base = tourFixtures.document.draft,
) {
  return base.replace("[Teacher decision needed: trial fee]", () =>
    decision === "answer"
      ? `About the trial fee: ${answer.trim()}`
      : "I'll confirm the trial fee with you before you decide.",
  );
}

interface TourStudent {
  id: string;
  name: string;
}
interface TourSession {
  id: string;
  className: string;
  date: string;
  time: string;
  location: string;
  capacity: number;
  students: TourStudent[];
}
export const tourBooking: { student: TourStudent; session: TourSession } = {
  student: { id: "3861ca04-d9bd-5994-af78-b1540c29f791", name: "Alex Morgan" },
  session: {
    id: "df96032d-5ce8-561e-948f-bda79b05887e",
    className: "Adult Ballet · Level 2",
    date: "Saturday 13 February 2027",
    time: "6 pm · Australia/Melbourne",
    location: "Merri Ballet · Brunswick",
    capacity: 2,
    students: [
      { id: "55c19f62-e578-4e33-9672-3dfe3fb65d3e", name: "Noah Ellis" },
    ],
  },
};
export type TourConfirmation =
  | { kind: "document"; approvedText: string }
  | {
      kind: "booking";
      approvedText: string;
      student: TourStudent;
      session: TourSession;
      before: TourStudent[];
      after: TourStudent[];
    };

export function createConfirmation(
  scenario: TourScenario,
  approvedText: string,
): TourConfirmation {
  if (scenario === "document") return { kind: "document", approvedText };
  const student = { ...tourBooking.student };
  const before = tourBooking.session.students.map((member) => ({ ...member }));
  const after = before.some((member) => member.id === student.id)
    ? [...before]
    : [...before, student];
  return {
    kind: "booking",
    approvedText,
    student,
    session: { ...tourBooking.session, students: before },
    before,
    after,
  };
}
