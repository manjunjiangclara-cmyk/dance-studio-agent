import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  tourBooking,
  tourFixtures,
  tourSource,
  type TourScenario,
} from "./tourData";
import { useLiveDemo } from "./useLiveDemo";

const cases: {
  scenario: TourScenario;
  subject: string;
  email: string;
  received: string;
  messageTimes: string[];
}[] = [
  {
    scenario: "booking",
    subject: "Makeup for Monday 8 February",
    email: "alex@example.test",
    received: "2027-02-07",
    messageTimes: ["2027-02-07T10:00:00+11:00", "2027-02-07T10:05:00+11:00"],
  },
  {
    scenario: "document",
    subject: "Questions about starting ballet",
    email: "jules@example.test",
    received: "2027-02-07",
    messageTimes: ["2027-02-07T10:00:00+11:00"],
  },
];
const formatReceived = (date: string) =>
  new Intl.DateTimeFormat("en-AU", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(`${date}T00:00:00Z`));

function evidenceInfo(entry: string) {
  if (entry.startsWith("Alex's original email asks"))
    return {
      label: "Email context",
      summary:
        "Alex's latest email changes the preferred day from Thursday to Saturday.",
      source: "email",
    };
  if (entry.startsWith("The fictional absence notice"))
    return {
      label: "Absence notice",
      summary: "The absence notice arrived before the missed class began.",
      source: "fact",
    };
  if (entry.startsWith("Alex has recorded Level 2 attendance"))
    return {
      label: "Attendance & policy",
      summary:
        "The example policy allows a Level 2 replacement when the notice is timely.",
      source: "fact",
    };
  if (entry.startsWith("Saturday 13 February 2027, 6 pm"))
    return {
      label: "Class availability",
      summary:
        "The Saturday Level 2 class has one place available in this example.",
      source: "fact",
    };
  if (entry.startsWith("Beginner clothing policy, revision 1:"))
    return {
      label: "Studio policy",
      summary:
        "Comfortable clothes and socks are suitable; ballet shoes are optional.",
      source: "policy",
    };
  if (entry.startsWith("No trial fee is specified"))
    return {
      label: "Missing fee information",
      summary: "The fictional policy does not specify the trial fee.",
      source: "policy",
    };
  return { label: "Supporting information", summary: entry, source: "fact" };
}

export function LiveReviewQueue() {
  return (
    <>
      <header className="page-heading">
        <div>
          <div className="eyebrow">EMAILS → CONTEXT → DRAFTS</div>
          <h1>The review queue.</h1>
          <p>
            Choose a fictional enquiry to see the email and supporting context,
            then generate a fresh AI response to review.
          </p>
        </div>
      </header>
      <div className="panel live-queue-panel">
        <LiveReviewCases />
      </div>
    </>
  );
}

export function LiveReviewCases() {
  return (
    <div className="run-list">
      {cases.map((item) => (
        <Link
          className="run-row"
          key={item.scenario}
          to={`/demo/reviews/live-${item.scenario}`}
        >
          <span className="avatar">
            {item.scenario === "booking" ? "AM" : "JP"}
          </span>
          <span className="run-person">
            <strong>{item.subject}</strong>
            <span>{item.email}</span>
          </span>
          <span className="run-meta live-case-date">
            <time dateTime={item.received}>
              {formatReceived(item.received)}
            </time>
          </span>
        </Link>
      ))}
    </div>
  );
}

export function LiveReviewDetail({ scenario }: { scenario: TourScenario }) {
  const live = useLiveDemo(scenario);
  const [decision, setDecision] = useState("");
  const [answer, setAnswer] = useState("");
  const [edited, setEdited] = useState<string | null>(null);
  const [approved, setApproved] = useState(false);
  const [answersLocked, setAnswersLocked] = useState(false);
  const item = cases.find((item) => item.scenario === scenario)!;
  const body = edited ?? live.draft ?? "";
  const [working, setWorking] = useState(false);
  const generating = useRef(false);
  async function generate() {
    if (generating.current) return;
    const willGenerateDraft = scenario === "booking" || Boolean(live.evidence);
    if (
      willGenerateDraft &&
      edited?.trim() &&
      !window.confirm(
        "Generating a draft will replace what you wrote. Continue?",
      )
    )
      return;
    generating.current = true;
    setWorking(true);
    try {
      if (!live.evidence) {
        const found = await live.execute("evidence");
        if (!found || scenario === "document") return;
      }
      if (
        scenario === "document" &&
        (!decision || (decision === "answer" && !answer.trim()))
      )
        return;
      setAnswersLocked(true);
      const generated = await live.execute(
        "draft",
        scenario === "document"
          ? [
              decision === "defer"
                ? "I will confirm the trial fee later."
                : answer.trim(),
            ]
          : [],
      );
      if (generated) setEdited(null);
    } finally {
      generating.current = false;
      setWorking(false);
    }
  }
  const formatTime = (date: string) =>
    new Intl.DateTimeFormat("en-AU", {
      hour: "numeric",
      minute: "2-digit",
      timeZone: "Australia/Melbourne",
    }).format(new Date(date));
  return (
    <>
      <Link className="back-link" to="/demo/reviews">
        ← Review queue
      </Link>
      <header className="page-heading">
        <div>
          <div className="eyebrow">LIVE AI · FICTIONAL ENQUIRY</div>
          <h1>{item.subject}</h1>
          <p>
            From {item.email} · Received{" "}
            <time dateTime={item.received}>
              {formatReceived(item.received)}
            </time>
          </p>
        </div>
      </header>
      <div className="notice">
        <ul className="notice-list">
          <li>Drafts and results disappear when you leave or refresh.</li>
          <li>Starting a draft uses one of 20 shared daily runs.</li>
          <li>
            Approval is simulated: no email is sent and no studio records are
            changed.
          </li>
        </ul>
      </div>
      <section className="panel" aria-labelledby="conversation-heading">
        <div className="live-conversation-heading">
          <div>
            <h2 id="conversation-heading">Student email</h2>
            <p>Conversation in the order received</p>
          </div>
          <span>
            {tourFixtures[scenario].messages.length}{" "}
            {tourFixtures[scenario].messages.length === 1
              ? "message"
              : "messages"}
          </span>
        </div>
        <ol
          className="live-conversation"
          aria-label="Student email conversation"
        >
          {tourFixtures[scenario].messages.map((message, index) => (
            <li
              className="live-conversation-message"
              key={`${message.sender}-${index}`}
            >
              <span className="live-conversation-avatar" aria-hidden="true">
                {scenario === "booking" ? "AM" : "JP"}
              </span>
              <div className="live-conversation-content">
                <div className="live-conversation-sender">
                  <time dateTime={item.messageTimes[index]}>
                    {formatTime(item.messageTimes[index])}
                  </time>
                </div>
                <div className="live-conversation-bubble">{message.body}</div>
              </div>
            </li>
          ))}
        </ol>
      </section>
      <section className="panel" aria-labelledby="draft-heading">
        <h2 id="draft-heading">Draft email</h2>
        {!live.draft && (
          <p>
            Generate a response based on the email and available studio
            information. Review it before approving.
          </p>
        )}
        <label
          className="editor-label live-draft-editor"
          htmlFor="live-review-response"
        >
          Response
          <textarea
            id="live-review-response"
            rows={10}
            value={body}
            placeholder="Write a response or generate a draft."
            disabled={working || Boolean(live.busy) || approved}
            onChange={(event) => setEdited(event.target.value)}
          />
        </label>
        {scenario === "document" && live.evidence && !live.draft && (
          <div className="tour-decision">
            <p>
              The fictional policy does not specify a trial fee. Choose how to
              respond before generating.
            </p>
            <label>
              <input
                type="radio"
                name="fee"
                disabled={answersLocked}
                checked={decision === "defer"}
                onChange={() => setDecision("defer")}
              />{" "}
              Confirm the fee later
            </label>
            <label>
              <input
                type="radio"
                name="fee"
                disabled={answersLocked}
                checked={decision === "answer"}
                onChange={() => setDecision("answer")}
              />{" "}
              Provide a fee answer
            </label>
            {decision === "answer" && (
              <label>
                Trial fee answer
                <input
                  value={answer}
                  disabled={answersLocked}
                  onChange={(event) => setAnswer(event.target.value)}
                  maxLength={2000}
                />
              </label>
            )}
            {answersLocked && live.error && (
              <p className="muted">
                Your decision is locked for this attempt so a retry uses the
                same answer. To change it, leave and reopen this enquiry; a new
                attempt uses another daily run.
              </p>
            )}
          </div>
        )}
        {!live.draft && (
          <button
            className="button primary live-draft-generate"
            disabled={
              working ||
              Boolean(live.busy) ||
              (scenario === "document" &&
                Boolean(live.evidence) &&
                (!decision || (decision === "answer" && !answer.trim())))
            }
            onClick={() => void generate()}
          >
            {working || live.busy
              ? "Generating draft…"
              : live.evidence && scenario === "document"
                ? "Generate draft with decision"
                : "Generate draft"}
          </button>
        )}
        {(working || live.busy) && (
          <p role="status">
            {live.busy === "evidence"
              ? "Checking relevant studio information…"
              : "Writing your draft…"}
          </p>
        )}
        {live.draft && (
          <>
            <p className="muted">
              Generated live · {live.model} · Review before approving
            </p>
            {scenario === "booking" && !approved && (
              <p className="muted footnote">
                Approving simulates a booking for{" "}
                {tourBooking.session.className} on {tourBooking.session.date} at{" "}
                {tourBooking.session.time}, {tourBooking.session.location}.
                Editing the email does not change the selected class.
              </p>
            )}
            <button
              className="button primary"
              disabled={!body.trim() || approved}
              onClick={() => setApproved(true)}
            >
              {approved ? "Approved" : "Approve response"}
            </button>
            {approved && scenario === "booking" && (
              <>
                <hr className="live-booking-divider" />
                <section
                  className="live-booking-card"
                  aria-labelledby="live-booking-heading"
                >
                  <div className="live-booking-card-header">
                    <div>
                      <div className="eyebrow">MAKEUP CLASS</div>
                      <h3 id="live-booking-heading">Booking confirmed</h3>
                    </div>
                    <span className="live-booking-badge">Simulation</span>
                  </div>
                  <p className="live-booking-class">
                    {tourBooking.session.className}
                  </p>
                  <dl className="live-booking-facts">
                    <div>
                      <dt>Student</dt>
                      <dd>{tourBooking.student.name}</dd>
                    </div>
                    <div>
                      <dt>Date</dt>
                      <dd>{tourBooking.session.date}</dd>
                    </div>
                    <div>
                      <dt>Time</dt>
                      <dd>{tourBooking.session.time}</dd>
                    </div>
                    <div>
                      <dt>Location</dt>
                      <dd>{tourBooking.session.location}</dd>
                    </div>
                  </dl>
                  <p className="live-booking-note">
                    Simulated booking only. No place was reserved and no email
                    was sent.
                  </p>
                </section>
              </>
            )}
          </>
        )}
        {live.error && (
          <div className="notice error" role="alert">
            <p>{live.error}</p>
            <button
              className="button secondary"
              disabled={working || Boolean(live.busy)}
              onClick={() => void generate()}
            >
              Retry
            </button>
          </div>
        )}
        {live.draft && live.evidence && (
          <div className="live-draft-evidence">
            <h3>Supporting evidence</h3>
            <ul className="live-evidence-list">
              {live.evidence.map((entry, i) => {
                const info = evidenceInfo(entry);
                return (
                  <li className="live-evidence-card" key={`${i}-${entry}`}>
                    <div className="live-evidence-card-heading">
                      <span className="live-evidence-number" aria-hidden="true">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <strong>{info.label}</strong>
                    </div>
                    <p>{info.summary}</p>
                    <details className="live-evidence-detail">
                      <summary>View source</summary>
                      <div className="live-evidence-original">
                        <strong>Fictional demo input</strong>
                        <p>{entry}</p>
                        {info.source === "email" && (
                          <a href="#conversation-heading">
                            View original student emails ↑
                          </a>
                        )}
                        {info.source === "policy" && (
                          <>
                            <strong>{tourSource.title} · Revision 1</strong>
                            <p>{tourSource.text}</p>
                          </>
                        )}
                      </div>
                    </details>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </section>
    </>
  );
}
