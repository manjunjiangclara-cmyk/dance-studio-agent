import { useEffect, useRef, useState } from "react";
import { Mail } from "lucide-react";
import { DraftEmailEditor } from "./DraftEmailEditor";
import { StudentEmailCard } from "./StudentEmailCard";
import { examples, request } from "./data";
import { SupportingEvidence } from "./SupportingEvidence";
import { StudentMemorySections } from "./StudentMemorySections";
import "./custom-email.css";

type Evidence = {
  evidence: string[];
  route: string;
  missing_information: string[];
  student_information?: string[];
  model: string;
};
type Turn = {
  request_id: string;
  email: string;
  reply: string | null;
  offer_confirmed: boolean;
  evidence: Evidence | null;
  draft: { body: string } | null;
  draft_answers: string[] | null;
};
type Thread = {
  student: string;
  state: {
    intents: string[];
    experience_level: string | null;
    preferred_day: string | null;
    recommended_class: { description: string } | null;
    customer_name: string | null;
    revision: number;
    booking_status: string;
    missing_information: string[];
    next_action: string;
  };
  turns: Turn[];
};
const key = "email-walkthrough-thread";
const legacyIds: Record<string, string> = {
  "3861ca04-d9bd-5994-af78-b1540c29f791": "alex",
  "153dbe65-4865-5343-93a0-f9fa60a4f6e2": "jules",
};

export function CustomEmail() {
  const [token, setToken] = useState(() => sessionStorage.getItem(key) || "");
  const initialToken = useRef(token);
  const [thread, setThread] = useState<Thread | null>(null);
  const [student, setStudent] = useState("new");
  const selectedStudent = examples.students.find(
    (s) => (legacyIds[s.id] || s.id) === student,
  );
  const [body, setBody] = useState("");
  const [reply, setReply] = useState("");
  const [offerConfirmed, setOfferConfirmed] = useState(false);
  const [answers, setAnswers] = useState<string[]>([]);
  const [answersLocked, setAnswersLocked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false);
  const requestId = useRef<string | null>(null);
  const headers = (value: string) => ({
    "Content-Type": "application/json",
    Authorization: `Bearer ${value}`,
  });
  async function load(value: string) {
    const data = await request<Thread>("/api/public-demo/threads/current", {
      method: "POST",
      headers: headers(value),
      body: "{}",
    });
    setThread(data);
    setStudent(data.student);
    const last = data.turns.at(-1);
    if (last && !last.reply) {
      setReply(last.draft?.body || "");
      setAnswers(
        last.draft_answers ??
          last.evidence?.missing_information.map(() => "") ??
          [],
      );
      setAnswersLocked(last.draft_answers != null);
    }
    return data;
  }
  useEffect(() => {
    if (initialToken.current)
      void load(initialToken.current).catch((e: Error) => setError(e.message));
  }, []);
  async function run(action: () => Promise<void>) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "The simulation could not complete.",
      );
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  async function submit() {
    if (!body.trim()) return;
    await run(async () => {
      let current = token;
      if (!current) {
        const created = await request<{ token: string }>(
          "/api/public-demo/threads",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student }),
          },
        );
        current = created.token;
        sessionStorage.setItem(key, current);
        setToken(current);
      }
      const id = requestId.current || crypto.randomUUID();
      requestId.current = id;
      await request("/api/public-demo/threads/current/turns", {
        method: "POST",
        headers: headers(current),
        body: JSON.stringify({ request_id: id, email_body: body }),
      });
      await load(current);
      setBody("");
      requestId.current = null;
      await request(`/api/public-demo/threads/current/turns/${id}/evidence`, {
        method: "POST",
        headers: headers(current),
        body: "{}",
      });
      await load(current);
    });
  }
  const current = thread?.turns.at(-1);
  const active = current && !current.reply ? current : null;
  const evidence = current?.evidence?.evidence ?? [];
  const trialOption =
    thread?.state.booking_status === "offered"
      ? thread.state.recommended_class
      : null;
  const trialReady =
    !active && thread?.state.booking_status === "awaiting_approval";
  const trialApproved = thread?.state.booking_status === "approved_mock";
  async function generate() {
    if (!active || !token) return;
    await run(async () => {
      try {
        const result = await request<{ body: string }>(
          `/api/public-demo/threads/current/turns/${active.request_id}/draft`,
          {
            method: "POST",
            headers: headers(token),
            body: JSON.stringify({
              teacher_answers: active.evidence!.missing_information.map(
                (_, i) =>
                  answers[i]?.trim() ||
                  "I will confirm this information later.",
              ),
            }),
          },
        );
        await load(token);
        setReply(result.body);
      } catch (error) {
        // The backend binds responses before calling the model, including on failure.
        await load(token).catch(() => {});
        throw error;
      }
    });
  }
  async function accept() {
    if (!active || !token) return;
    await run(async () => {
      await request(
        `/api/public-demo/threads/current/turns/${active.request_id}/accept`,
        {
          method: "POST",
          headers: headers(token),
          body: JSON.stringify({
            body: reply,
            offer_confirmed: offerConfirmed,
          }),
        },
      );
      await load(token);
      setReply("");
      setOfferConfirmed(false);
    });
  }
  async function approve() {
    if (!thread || !token) return;
    await run(async () => {
      await request("/api/public-demo/threads/current/approve", {
        method: "POST",
        headers: headers(token),
        body: JSON.stringify({ revision: thread.state.revision }),
      });
      await load(token);
    });
  }
  function reset() {
    sessionStorage.removeItem(key);
    setToken("");
    setThread(null);
    setBody("");
    setReply("");
    setOfferConfirmed(false);
    setError("");
    requestId.current = null;
  }
  return (
    <>
      <header className="page-heading">
        <div>
          <div className="eyebrow">EMAIL WALKTHROUGH</div>
          <h1>Try a conversation.</h1>
          <p>
            Write fictional emails and see how the copilot prepares responses.
          </p>
        </div>
      </header>
      <div className="review-flow custom-email-flow">
        <section className="panel email-form">
          <div className="section-heading compact">
            <div>
              <div className="eyebrow">EMAIL WALKTHROUGH</div>
              <h2>Write a student email</h2>
            </div>
            <Mail size={17} aria-hidden="true" />
          </div>
          <label htmlFor="demo-student">Sender context</label>
          <select
            id="demo-student"
            value={student}
            disabled={Boolean(token) || busy}
            onChange={(e) => setStudent(e.target.value)}
          >
            <option value="new">New enquirer · no history</option>
            {examples.students.map((s) => (
              <option key={s.id} value={legacyIds[s.id] || s.id}>
                {s.display_name}
              </option>
            ))}
          </select>
          <label htmlFor="demo-email-body">Email body</label>
          {current?.reply && (
            <>
              {trialOption &&
                (current.offer_confirmed ? (
                  <p>
                    To request this trial as the student, reply “Yes, please”.
                  </p>
                ) : (
                  <p>
                    To continue the trial, send another student email about the
                    class and confirm the next offer before accepting the reply.
                  </p>
                ))}
              {thread?.state.booking_status === "collecting_name" && (
                <p>Reply with your name, for example “My name is Taylor”.</p>
              )}
            </>
          )}
          <textarea
            id="demo-email-body"
            rows={8}
            maxLength={2000}
            value={body}
            disabled={busy || Boolean(active)}
            onChange={(e) => {
              setBody(e.target.value);
              requestId.current = null;
            }}
            placeholder="Write a fictional enquiry…"
          />
          <p className="muted">{body.length}/2000 characters</p>
          <div className="notice email-notice">
            <ul>
              <li>Use fictional content only.</li>
              <li>Hosted demos share 20 live runs per day.</li>
              <li>
                Conversations expire after one hour or at the end of the
                Melbourne day.
              </li>
              <li>No email is sent and no studio records are changed.</li>
            </ul>
          </div>
          {error && <p role="alert">{error}</p>}
          <button
            className="button primary"
            disabled={busy || !body.trim() || Boolean(active)}
            onClick={() => void submit()}
          >
            {busy ? "Processing…" : "Simulate email"}
          </button>{" "}
          <button className="button secondary" disabled={busy} onClick={reset}>
            Start new conversation
          </button>
        </section>
        {current && thread && (
          <StudentEmailCard
            name={selectedStudent?.display_name ?? "New enquirer"}
            messages={thread.turns.flatMap((turn) => [
              { body: turn.email },
              ...(turn.reply
                ? [{ body: turn.reply, sender: "teacher" as const }]
                : []),
            ])}
          />
        )}
        {active && (
          <section
            className="panel custom-email-result"
            aria-labelledby="walkthrough-response-title"
          >
            <DraftEmailEditor
              headingId="walkthrough-response-title"
              inputId="reply"
              value={reply}
              onChange={(value) => {
                setReply(value);
                setOfferConfirmed(false);
              }}
              disabled={busy || !active.draft}
              placeholder="Generate a draft to prepare a response."
              description={
                !active.draft
                  ? "Generate a response based on the email and available studio information. Review it before accepting."
                  : undefined
              }
              maxLength={5000}
            />
            {active.evidence ? (
              <>
                {Boolean(active.evidence.student_information?.length) && (
                  <section
                    className="walkthrough-information"
                    aria-labelledby="student-information-title"
                  >
                    <h3 id="student-information-title">
                      Information to ask the student
                    </h3>
                    <ul>
                      {active.evidence.student_information?.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </section>
                )}
                {active.evidence.missing_information.length > 0 && (
                  <section
                    className="walkthrough-information"
                    aria-labelledby="teacher-information-title"
                  >
                    <h3 id="teacher-information-title">
                      Information to confirm
                    </h3>
                    <p>
                      Add what you know below. If left blank, the draft will say
                      you’ll confirm it later.
                    </p>
                    {active.evidence.missing_information.map((item, i) => (
                      <div className="walkthrough-information-field" key={i}>
                        <label htmlFor={`missing-${i}`}>{item}</label>
                        <textarea
                          id={`missing-${i}`}
                          rows={3}
                          placeholder="Add details (optional)"
                          value={answers[i] || ""}
                          disabled={
                            busy || answersLocked || Boolean(active.draft)
                          }
                          onChange={(e) =>
                            setAnswers((a) =>
                              a.map((x, j) => (j === i ? e.target.value : x)),
                            )
                          }
                        />
                      </div>
                    ))}
                  </section>
                )}
                {!active.draft && (
                  <button
                    className="button primary"
                    disabled={busy}
                    onClick={() => void generate()}
                  >
                    Generate draft
                  </button>
                )}
              </>
            ) : (
              <button
                className="button secondary"
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    await request(
                      `/api/public-demo/threads/current/turns/${active.request_id}/evidence`,
                      { method: "POST", headers: headers(token), body: "{}" },
                    );
                    await load(token);
                  })
                }
              >
                Retry evidence
              </button>
            )}
            {active.draft && (
              <>
                {trialOption && (
                  <section
                    className="walkthrough-information"
                    aria-labelledby="trial-option-title"
                  >
                    <h3 id="trial-option-title">Trial class option</h3>
                    <p>{trialOption.description}</p>
                    <label>
                      <input
                        type="checkbox"
                        checked={offerConfirmed}
                        disabled={busy}
                        onChange={(e) => setOfferConfirmed(e.target.checked)}
                      />
                      I’ve reviewed the student’s experience and confirm this
                      reply invites them to request a trial in this class,
                      subject to teacher confirmation of placement.
                    </label>
                    <p>
                      Check this box before accepting the reply if you want the
                      student to be able to request this trial in the next
                      email.
                    </p>
                  </section>
                )}
                <button
                  className="button primary"
                  disabled={busy || !reply.trim()}
                  onClick={() => void accept()}
                >
                  Accept simulated reply
                </button>
                <p>No email was sent or class booked.</p>
              </>
            )}
          </section>
        )}
        {current && evidence.length > 0 && (
          <section
            className="panel walkthrough-evidence"
            aria-label="Supporting evidence"
            key={current.request_id}
          >
            <SupportingEvidence evidence={evidence} showConversationLink />
          </section>
        )}
        {(trialReady || trialApproved) && (
          <section className="panel" aria-labelledby="walkthrough-trial-title">
            <h2 id="walkthrough-trial-title">Trial request</h2>
            {thread?.state.recommended_class && (
              <p>{thread.state.recommended_class.description}</p>
            )}
            {trialReady ? (
              <button
                className="button secondary"
                disabled={busy}
                onClick={() => void approve()}
              >
                Approve mock request
              </button>
            ) : (
              <p role="status">
                Mock request approved. No real booking was made.
              </p>
            )}
          </section>
        )}
        <details className="panel review-support custom-email-support">
          <summary>Enquiry state and student context</summary>
          <div className="custom-email-context">
            <h2>Enquiry state</h2>
            {thread ? (
              <dl>
                <dt>Intents</dt>
                <dd>{thread.state.intents.join(", ") || "Not identified"}</dd>
                <dt>Experience</dt>
                <dd>{thread.state.experience_level || "Not provided"}</dd>
                <dt>Preferred day</dt>
                <dd>{thread.state.preferred_day || "Not provided"}</dd>
                <dt>Class option</dt>
                <dd>
                  {thread.state.recommended_class?.description ||
                    "Teacher confirmation needed"}
                </dd>
                <dt>Name</dt>
                <dd>{thread.state.customer_name || "Not provided"}</dd>
                <dt>Status</dt>
                <dd>{thread.state.booking_status.replaceAll("_", " ")}</dd>
                <dt>Next action</dt>
                <dd>{thread.state.next_action.replaceAll("_", " ")}</dd>
              </dl>
            ) : (
              <p>No conversation yet.</p>
            )}
            <h2>About this student</h2>
            <StudentMemorySections
              context={selectedStudent?.context ?? {}}
              summary={selectedStudent?.ai_summary ?? null}
            />
          </div>
        </details>
      </div>
    </>
  );
}
