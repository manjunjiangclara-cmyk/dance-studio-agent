import { useEffect, useRef, useState } from "react";
import { ApiError, examples, request } from "./data";
import { StudentMemorySections } from "./StudentMemorySections";
import { DraftEmailEditor } from "./DraftEmailEditor";
import { SupportingEvidence } from "./SupportingEvidence";
import "./custom-email.css";

// Preserve the original IDs for in-flight and retryable simulations.
const legacyStudentIds: Record<string, string> = {
  "3861ca04-d9bd-5994-af78-b1540c29f791": "alex",
  "153dbe65-4865-5343-93a0-f9fa60a4f6e2": "jules",
};
const students = examples.students.map((student) => ({
  ...student,
  simulationId: legacyStudentIds[student.id] ?? student.id,
}));
type Student = string;
interface Evidence {
  evidence: string[];
  route: "enquiry" | "makeup" | "teacher_handoff";
  missing_information: string[];
  student_information?: string[];
  model: string;
}
interface Attempt {
  student: Student;
  email: string;
  requestId: string;
  token?: string;
  evidence?: Evidence;
  draft?: string;
}
export function CustomEmail() {
  const [student, setStudent] = useState<Student>("new");
  const selectedStudent = students.find(
    (item) => item.simulationId === student,
  );
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState("");
  const [error, setError] = useState("");
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [draft, setDraft] = useState("");
  const [generated, setGenerated] = useState(false);
  const [answers, setAnswers] = useState<string[]>([]);
  const [answersLocked, setAnswersLocked] = useState(false);
  const attempt = useRef<Attempt | null>(null);
  const simulationPending = useRef(false);
  const draftPending = useRef(false);
  const alive = useRef(true);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  function invalidate() {
    attempt.current = null;
    if (draftPending.current) {
      draftPending.current = false;
      setBusy(false);
      setStage("");
    }
    setError("");
    setEvidence(null);
    setDraft("");
    setGenerated(false);
    setAnswers([]);
    setAnswersLocked(false);
  }
  async function simulate() {
    if (simulationPending.current || !body.trim()) return;
    const current = evidence
      ? { student, email: body, requestId: crypto.randomUUID() }
      : attempt.current || {
          student,
          email: body,
          requestId: crypto.randomUUID(),
        };
    if (evidence) invalidate();
    attempt.current = current;
    simulationPending.current = true;
    draftPending.current = false;
    setBusy(true);
    setError("");
    try {
      if (!current.token) {
        setStage("Starting simulation…");
        const run = await request<{ token: string }>("/api/public-demo/runs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            scenario: "custom",
            student: current.student,
            email_body: current.email,
            request_id: current.requestId,
          }),
        });
        if (!alive.current || attempt.current !== current) return;
        current.token = run.token;
      }
      const headers = {
        "Content-Type": "application/json",
        Authorization: `Bearer ${current.token}`,
      };
      if (!current.evidence) {
        setStage("Finding supporting evidence…");
        current.evidence = await request<Evidence>(
          "/api/public-demo/evidence",
          { method: "POST", headers, body: "{}" },
        );
        if (!alive.current || attempt.current !== current) return;
      }
      setEvidence(current.evidence);
      setAnswers(current.evidence.missing_information.map(() => ""));
      requestAnimationFrame(() => {
        if (alive.current) resultHeading.current?.focus();
      });
    } catch (caught) {
      if (alive.current && attempt.current === current)
        setError(
          caught instanceof ApiError && caught.status === 0
            ? "Connection interrupted. Retry to recover this simulation."
            : caught instanceof Error
              ? caught.message
              : "The email simulation could not complete.",
        );
    } finally {
      simulationPending.current = false;
      if (alive.current && attempt.current === current) {
        setBusy(false);
        setStage("");
      }
    }
  }
  async function generateDraft() {
    const current = attempt.current;
    if (
      !current?.token ||
      !current.evidence ||
      simulationPending.current ||
      draftPending.current ||
      answers.some((a) => !a.trim()) ||
      answers.length !== current.evidence.missing_information.length
    )
      return;
    draftPending.current = true;
    setBusy(true);
    setAnswersLocked(true);
    setError("");
    setStage("Generating draft…");
    try {
      const result = await request<{ body: string }>("/api/public-demo/draft", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${current.token}`,
        },
        body: JSON.stringify({ teacher_answers: answers }),
      });
      if (!result.body?.trim())
        throw new Error(
          "The live service returned an empty draft. Retry this step.",
        );
      if (alive.current && attempt.current === current) {
        current.draft = result.body;
        setDraft(result.body);
        setGenerated(true);
      }
    } catch (caught) {
      if (alive.current && attempt.current === current)
        setError(
          caught instanceof Error
            ? caught.message
            : "The draft could not be generated.",
        );
    } finally {
      if (alive.current && attempt.current === current) {
        draftPending.current = false;
        setBusy(false);
        setStage("");
      }
    }
  }
  return (
    <>
      <header className="page-heading">
        <div>
          <div className="eyebrow">EMAIL WALKTHROUGH</div>
          <h1>Try an email of your own.</h1>
          <p>
            Write a fictional email and see how the copilot prepares a response.
          </p>
        </div>
      </header>
      <div className="email-grid">
        <section
          className="panel email-form"
          aria-labelledby="custom-email-title"
        >
          <h2 id="custom-email-title">Simulate an incoming email</h2>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void simulate();
            }}
          >
            <label htmlFor="demo-student">Sender context</label>
            <select
              id="demo-student"
              value={student}
              disabled={busy && !evidence}
              onChange={(event) => {
                setStudent(event.target.value as Student);
                invalidate();
              }}
            >
              <option value="new">New enquirer · no history</option>
              {students.map((item) => (
                <option key={item.id} value={item.simulationId}>
                  {item.display_name}
                </option>
              ))}
            </select>
            <label htmlFor="demo-email-body">Email body</label>
            <textarea
              id="demo-email-body"
              rows={9}
              maxLength={2000}
              required
              value={body}
              disabled={busy && !evidence}
              placeholder="Write a fictional enquiry or makeup request…"
              onChange={(event) => {
                setBody(event.target.value);
                invalidate();
              }}
            />
            <p className="muted custom-email-limit">
              {body.length}/2000 characters
            </p>
            <div className="notice email-notice" role="note">
              <ul className="notice-list">
                <li>Use fictional content only.</li>
                <li>Live AI shares the limit of 20 demo runs per day.</li>
                <li>Results are unavailable after you leave or refresh.</li>
                <li>No email is sent and no studio records are changed.</li>
              </ul>
            </div>
            {error && !evidence && (
              <div role="alert">
                <p>{error}</p>
                <button
                  type="button"
                  className="button secondary"
                  disabled={busy}
                  onClick={() => void simulate()}
                >
                  Retry
                </button>
              </div>
            )}
            <button
              className="button primary"
              disabled={!body.trim() || (busy && !evidence)}
            >
              {busy && !evidence ? "Simulating email…" : "Simulate email"}
            </button>
            {busy && !evidence && <p role="status">{stage}</p>}
          </form>
        </section>
        <aside className="panel context-card profile-card profile-memory email-explainer">
          <div className="eyebrow">CONVERSATION MEMORY</div>
          <h2>About this student</h2>
          <p className="profile-card-description">
            Details and preferences shared in conversations
          </p>
          <StudentMemorySections
            context={selectedStudent?.context ?? {}}
            summary={selectedStudent?.ai_summary ?? null}
          />
        </aside>
      </div>
      {evidence && (
        <section
          className="panel custom-email-result"
          aria-labelledby="custom-result-title"
        >
          <DraftEmailEditor
            headingId="custom-result-title"
            headingRef={resultHeading}
            inputId="custom-response"
            value={draft}
            onChange={setDraft}
            disabled={!generated || busy}
            placeholder="Generate a draft to prepare a response."
            maxLength={5000}
            showEditor={generated}
          />
          <p className="custom-route">
            {evidence.route === "makeup"
              ? "Makeup request"
              : evidence.route === "teacher_handoff"
                ? "Needs teacher review"
                : "Enquiry"}{" "}
            · {evidence.model}
          </p>
          {Boolean(evidence.student_information?.length) && (
            <section
              className="student-clarification"
              aria-labelledby="student-clarification-title"
            >
              <h3 id="student-clarification-title">
                Information to ask the student
              </h3>
              <p>The draft will ask the student for these details.</p>
              <ul>
                {evidence.student_information?.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </section>
          )}
          {evidence.missing_information.length > 0 && (
            <section aria-label="Information needed from teacher">
              <h3>Information needed from teacher</h3>
              <p>
                Provide a response for each item, or say you will confirm it
                later. These responses will be used to generate the draft.
              </p>
              {evidence.missing_information.map((item, index) => (
                <div key={index}>
                  <label htmlFor={`missing-${index}`}>{item}</label>
                  <textarea
                    id={`missing-${index}`}
                    maxLength={2000}
                    value={answers[index] || ""}
                    disabled={answersLocked || busy}
                    onChange={(event) =>
                      setAnswers((previous) =>
                        previous.map((value, i) =>
                          i === index ? event.target.value : value,
                        ),
                      )
                    }
                  />
                </div>
              ))}
            </section>
          )}
          {!generated && (
            <button
              className="button primary"
              disabled={
                busy ||
                answers.length !== evidence.missing_information.length ||
                answers.some((answer) => !answer.trim())
              }
              onClick={() => void generateDraft()}
            >
              Generate draft
            </button>
          )}
          {busy && <p role="status">{stage}</p>}
          {error && (
            <div role="alert">
              <p>{error}</p>
              <button
                className="button secondary"
                disabled={busy}
                onClick={() => void generateDraft()}
              >
                Retry draft
              </button>
            </div>
          )}
          {generated && (
            <p className="muted">
              Edit this draft locally. No email was sent or class booked.
            </p>
          )}
          {evidence.evidence.length ? (
            <SupportingEvidence evidence={evidence.evidence} />
          ) : (
            <div className="live-draft-evidence">
              <h3>Supporting evidence</h3>
              <p>
                No matching source was found; the response should ask for
                details or confirmation.
              </p>
            </div>
          )}
        </section>
      )}
    </>
  );
}
