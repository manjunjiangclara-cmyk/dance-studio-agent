import { useEffect, useRef, useState } from "react";
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
  evidence: Evidence | null;
  draft: { body: string } | null;
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
  const [answers, setAnswers] = useState<string[]>([]);
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
      setAnswers(last.evidence?.missing_information.map(() => "") || []);
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
      await request(`/api/public-demo/threads/current/turns/${id}/evidence`, {
        method: "POST",
        headers: headers(current),
        body: "{}",
      });
      await load(current);
      setBody("");
      requestId.current = null;
    });
  }
  const current = thread?.turns.at(-1);
  const active = current && !current.reply ? current : null;
  async function generate() {
    if (!active || !token) return;
    await run(async () => {
      const result = await request<{ body: string }>(
        `/api/public-demo/threads/current/turns/${active.request_id}/draft`,
        {
          method: "POST",
          headers: headers(token),
          body: JSON.stringify({ teacher_answers: answers }),
        },
      );
      await load(token);
      setReply(result.body);
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
          body: JSON.stringify({ body: reply }),
        },
      );
      await load(token);
      setReply("");
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
      <div className="email-grid">
        <section className="panel email-form">
          <h2>Simulate an incoming email</h2>
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
              <li>Each email uses one of 20 daily live demo runs.</li>
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
        <aside className="panel">
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
          {thread?.state.booking_status === "awaiting_approval" && !active && (
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => void approve()}
            >
              Approve mock request
            </button>
          )}
          {thread?.state.booking_status === "approved_mock" && (
            <p>Mock request approved. No real booking was made.</p>
          )}
          <h2>About this student</h2>
          <StudentMemorySections
            context={selectedStudent?.context ?? {}}
            summary={selectedStudent?.ai_summary ?? null}
          />
        </aside>
      </div>
      {thread && (
        <section className="panel custom-email-result">
          <h2>Conversation</h2>
          {thread.turns.map((t) => (
            <article key={t.request_id}>
              <h3>Customer email</h3>
              <p style={{ whiteSpace: "pre-wrap" }}>{t.email}</p>
              {t.reply && (
                <>
                  <h3>Accepted reply · simulated</h3>
                  <p style={{ whiteSpace: "pre-wrap" }}>{t.reply}</p>
                </>
              )}
            </article>
          ))}
        </section>
      )}
      {active && (
        <section className="panel custom-email-result">
          <h2>Draft email</h2>
          {active.evidence ? (
            <>
              <p>
                Information to ask the student:{" "}
                {active.evidence.student_information?.join(", ") ||
                  "None identified"}
              </p>
              {active.evidence.missing_information.map((item, i) => (
                <div key={i}>
                  <label htmlFor={`missing-${i}`}>{item}</label>
                  <textarea
                    id={`missing-${i}`}
                    value={answers[i] || ""}
                    disabled={busy || Boolean(active.draft)}
                    onChange={(e) =>
                      setAnswers((a) =>
                        a.map((x, j) => (j === i ? e.target.value : x)),
                      )
                    }
                  />
                </div>
              ))}
              {!active.draft && (
                <button
                  className="button primary"
                  disabled={busy || answers.some((a) => !a.trim())}
                  onClick={() => void generate()}
                >
                  Generate draft
                </button>
              )}
              {active.evidence.evidence.length > 0 && (
                <SupportingEvidence evidence={active.evidence.evidence} />
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
              <label htmlFor="reply">Response</label>
              <textarea
                id="reply"
                rows={8}
                maxLength={5000}
                value={reply}
                onChange={(e) => setReply(e.target.value)}
              />
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
    </>
  );
}
