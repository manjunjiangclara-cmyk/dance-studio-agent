import {
  useEffect,
  useRef,
  useState,
  type ComponentProps,
  type FormEvent,
} from "react";
import { examples } from "./data";
import { DemoResponse } from "./DemoResponse";
import { StudentEmailCard } from "./StudentEmailCard";
import { useLiveDemo, type WalkthroughRun } from "./useLiveDemo";

type CompletedTurn = {
  email: string;
  reply: string;
  booking?: string;
  bookingKind?: "trial" | "makeup";
  bookingDetails?: string;
};
type Session = {
  student: string;
  turns: CompletedTurn[];
  previousToken?: string;
  active?: WalkthroughRun;
  answers?: string[];
  answersWereSubmitted?: boolean;
  editedReply?: string | null;
};

const storageKey = "public-walkthrough-langgraph";
const emptySession = (): Session => ({ student: "new", turns: [] });

function loadSession(): Session {
  try {
    const stored = sessionStorage.getItem(storageKey);
    return stored ? JSON.parse(stored) : emptySession();
  } catch {
    return emptySession();
  }
}

export function EmailWalkthrough() {
  const [session, setSession] = useState(loadSession);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const student = examples.students.find(({ id }) => id === session.student);
  const messages = session.turns.flatMap(({ email, reply, bookingKind }) => [
    { body: email },
    {
      body: reply,
      sender: "teacher" as const,
      simulatedTrial: bookingKind === "trial",
    },
  ]);
  const latest = session.turns.at(-1);
  const active = session.active;
  if (active) messages.push({ body: active.email });

  function update(next: Session) {
    setSession(next);
    sessionStorage.setItem(storageKey, JSON.stringify(next));
  }

  function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!email.trim() || active) return;
    update({
      ...session,
      active: {
        requestId: crypto.randomUUID(),
        student: session.student,
        email: email.trim(),
        previousToken: session.previousToken,
        autoCheck: /\b(?:book|reserve|yes|go ahead)\b/i.test(email),
      },
    });
    setEmail("");
  }

  return (
    <>
      <header className="page-heading">
        <div>
          <h1>Email Walkthrough</h1>
          <p>
            Write a fictional student email and review the copilot’s response.
          </p>
        </div>
      </header>

      <div className="review-flow">
        <form className="panel email-form walkthrough-form" onSubmit={start}>
          <label htmlFor="walkthrough-student">Sender context</label>
          <select
            id="walkthrough-student"
            value={session.student}
            disabled={Boolean(active || session.previousToken)}
            onChange={(event) =>
              update({ ...session, student: event.target.value })
            }
          >
            <option value="new">New enquirer · no history</option>
            {examples.students.map(({ id, display_name }) => (
              <option key={id} value={id}>
                {display_name}
              </option>
            ))}
          </select>
          {!active && (
            <>
              <label htmlFor="walkthrough-email">
                {latest ? "Follow-up email" : "Student email"}
              </label>
              <textarea
                id="walkthrough-email"
                rows={6}
                maxLength={2000}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="Write a fictional enquiry…"
              />
              <button className="button primary" disabled={!email.trim()}>
                {latest ? "Add follow-up email" : "Simulate email"}
              </button>{" "}
            </>
          )}
          <button
            type="button"
            className="button secondary"
            disabled={busy || (!active && !latest && !email)}
            onClick={() => {
              update(emptySession());
              setEmail("");
            }}
          >
            Start new conversation
          </button>
          <p className="muted">
            Use fictional details only. A clear request for an available trial
            can be booked automatically in the simulation.
          </p>
        </form>
        {messages.length > 0 && (
          <StudentEmailCard
            name={student?.display_name || "New enquirer"}
            messages={messages}
          />
        )}
        {latest && !active && (
          <p className="notice" role="status">
            {latest.bookingKind === "trial"
              ? `Trial booked automatically in the simulation. ${latest.bookingDetails}.`
              : latest.booking
                ? `Simulated makeup booking for ${latest.booking}.`
                : "Response approved in the simulation."}{" "}
            No email was sent.
          </p>
        )}
        {active && (
          <WalkthroughReview
            key={active.requestId}
            input={active}
            answers={session.answers}
            answersWereSubmitted={session.answersWereSubmitted}
            onBusy={setBusy}
            savedEdit={session.editedReply}
            onEdit={(editedReply) => update({ ...session, editedReply })}
            onAnswers={(answers, answersWereSubmitted) =>
              update({ ...session, answers, answersWereSubmitted })
            }
            onApproved={(approval, token) =>
              update({
                student: session.student,
                previousToken: token,
                turns: [
                  ...session.turns,
                  {
                    email: active.email,
                    reply: approval.body,
                    booking: approval.booking?.session.className,
                    bookingKind: approval.booking_kind,
                    bookingDetails: approval.booking
                      ? `${approval.booking.session.className}, ${approval.booking.session.date} at ${approval.booking.session.time}, ${approval.booking.session.location}`
                      : undefined,
                  },
                ],
              })
            }
          />
        )}
      </div>
    </>
  );
}

function WalkthroughReview({
  input,
  answers,
  answersWereSubmitted,
  onBusy,
  savedEdit,
  onEdit,
  onAnswers,
  onApproved,
}: {
  input: WalkthroughRun;
  answers?: string[];
  answersWereSubmitted?: boolean;
  onBusy: (busy: boolean) => void;
  savedEdit?: string | null;
  onEdit: (body: string | null) => void;
  onAnswers: NonNullable<ComponentProps<typeof DemoResponse>["onAnswers"]>;
  onApproved: NonNullable<ComponentProps<typeof DemoResponse>["onApproved"]>;
}) {
  const live = useLiveDemo(input);
  const busy = Boolean(live.busy);
  const started = useRef(false);
  const saved = useRef(false);
  useEffect(() => onBusy(busy), [busy, onBusy]);
  useEffect(() => {
    if (input.autoCheck && !started.current) {
      started.current = true;
      void live.execute("evidence");
    }
  }, [input.autoCheck, live.execute]);
  useEffect(() => {
    if (live.automaticApproval && !saved.current) {
      saved.current = true;
      onBusy(false);
      onApproved(live.automaticApproval, live.runToken.current);
    }
  }, [live.automaticApproval, live.runToken, onApproved, onBusy]);
  return (
    <DemoResponse
      live={live}
      separateEvidence
      savedAnswers={answers}
      answersWereSubmitted={answersWereSubmitted}
      onAnswers={onAnswers}
      savedEdit={savedEdit}
      onEdit={onEdit}
      onApproved={(approval, token) => {
        onBusy(false);
        onApproved(approval, token);
      }}
    />
  );
}
