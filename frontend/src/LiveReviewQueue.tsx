import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { DraftEmailEditor } from "./DraftEmailEditor";
import { StudentEmailCard } from "./StudentEmailCard";
import { SupportingEvidence } from "./SupportingEvidence";
import { IntentBadges } from "./Classification";
import { tourBooking, tourFixtures, type TourScenario } from "./tourData";
import { useLiveDemo } from "./useLiveDemo";

type ReviewScenario = TourScenario | "noah" | "riley";
const cases: {
  scenario: ReviewScenario;
  name: string;
  studentId?: string;
  emailBody?: string;
  subject: string;
  email: string;
  description: string;
  intent: string;
  received: string;
  messageTimes: string[];
}[] = [
  {
    scenario: "booking",
    name: "Alex Morgan",
    subject: "Makeup for Monday 8 February",
    email: "alex@example.test",
    description: "Can't attend Monday and would prefer Saturday.",
    intent: "makeup",
    received: "2027-02-07",
    messageTimes: ["2027-02-07T10:00:00+11:00", "2027-02-07T10:05:00+11:00"],
  },
  {
    scenario: "document",
    name: "Jules Park",
    subject: "Questions about starting ballet",
    email: "jules@example.test",
    description: "Asks what to wear and how much a trial costs.",
    intent: "new_student_enquiry",
    received: "2027-02-07",
    messageTimes: ["2027-02-07T10:00:00+11:00"],
  },
  {
    scenario: "noah",
    name: "Noah Ellis",
    studentId: "60bbb539-91bc-5858-80f5-a1b6ae915aae",
    subject: "Makeup options for next week",
    email: "noah@example.test",
    emailBody: "Could I arrange a makeup class?",
    description: "Asks about arranging a makeup class.",
    intent: "makeup",
    received: "2027-02-07",
    messageTimes: ["2027-02-07T10:00:00+11:00"],
  },
  {
    scenario: "riley",
    name: "Riley James",
    studentId: "2eca4988-037e-54f9-9668-59ee06b2888b",
    subject: "Help choosing a ballet class",
    email: "riley@example.test",
    emailBody: "Could you help me choose a class?",
    description: "Asks for help choosing a class.",
    intent: "general_enquiry",
    received: "2027-02-07",
    messageTimes: ["2027-02-07T10:00:00+11:00"],
  },
];
const formatReceived = (date: string) =>
  new Intl.DateTimeFormat("en-AU", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(`${date}T00:00:00Z`));

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

function LiveReviewCases() {
  return (
    <div className="run-list">
      {cases.map((item) => (
        <Link
          className="run-row"
          key={item.scenario}
          to={`/demo/reviews/live-${item.scenario}`}
        >
          <span className="avatar">
            {item.name
              .split(" ")
              .map((part) => part[0])
              .join("")}
          </span>
          <div className="run-person">
            <strong>{item.subject}</strong>
            <span className="case-description">{item.description}</span>
            <IntentBadges routing={{ intents: [item.intent] }} />
          </div>
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

export function LiveReviewDetail({ scenario }: { scenario: ReviewScenario }) {
  const item = cases.find((entry) => entry.scenario === scenario)!;
  const custom = scenario === "noah" || scenario === "riley";
  const live = useLiveDemo(
    custom ? { student: item.studentId!, email: item.emailBody! } : scenario,
  );
  const messages =
    scenario === "booking" || scenario === "document"
      ? tourFixtures[scenario].messages
      : [{ sender: item.name, body: item.emailBody! }];
  const [teacherAnswers, setTeacherAnswers] = useState<string[]>([]);
  const [decision, setDecision] = useState("");
  const [answer, setAnswer] = useState("");
  const [edited, setEdited] = useState<string | null>(null);
  const [approved, setApproved] = useState(false);
  const [answersLocked, setAnswersLocked] = useState(false);
  const body = edited ?? live.draft ?? "";
  const [working, setWorking] = useState(false);
  const generating = useRef(false);
  async function generate() {
    if (generating.current) return;
    const willGenerateDraft = scenario !== "document" || Boolean(live.evidence);
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
        if (custom && found.missing_information?.length) {
          setTeacherAnswers(found.missing_information.map(() => ""));
          return;
        }
      }
      if (
        scenario === "document" &&
        (!decision || (decision === "answer" && !answer.trim()))
      )
        return;
      if (
        custom &&
        (teacherAnswers.length !== live.missingInformation.length ||
          teacherAnswers.some((value) => !value.trim()))
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
          : custom
            ? teacherAnswers
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
      <header className="page-heading live-review-header">
        <div>
          <div className="eyebrow">LIVE AI · FICTIONAL ENQUIRY</div>
          <h1>{item.subject}</h1>
          <p>
            From <span className="review-email-address">{item.email}</span> ·
            Received{" "}
            <time dateTime={item.received}>
              {formatReceived(item.received)}
            </time>
          </p>
          <div className="review-disclosure">
            <IntentBadges routing={{ intents: [item.intent] }} />
            <span>
              Approval is simulated: no email is sent and no studio records are
              changed.
            </span>
          </div>
        </div>
      </header>
      <div className="live-review-columns">
        <StudentEmailCard
          name={item.name}
          messages={messages.map((message, index) => ({
            body: message.body,
            dateTime: item.messageTimes[index],
            time: formatTime(item.messageTimes[index]),
          }))}
        />
        <section className="panel" aria-labelledby="draft-heading">
          <DraftEmailEditor
            headingId="draft-heading"
            inputId="live-review-response"
            value={body}
            onChange={setEdited}
            disabled={working || Boolean(live.busy) || approved}
            placeholder="Write a response or generate a draft."
            description={
              !live.draft
                ? "Generate a response based on the email and available studio information. Review it before approving."
                : undefined
            }
          />
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
                  same answer. To change it, leave and reopen this enquiry; a
                  new attempt uses another daily run.
                </p>
              )}
            </div>
          )}
          {custom &&
            live.evidence &&
            live.missingInformation.length > 0 &&
            !live.draft && (
              <div className="tour-decision">
                <p>
                  Provide an answer for each item, or say you will confirm it
                  later.
                </p>
                {live.missingInformation.map((question, index) => (
                  <label key={index}>
                    {question}
                    <textarea
                      value={teacherAnswers[index] || ""}
                      maxLength={2000}
                      disabled={answersLocked || working}
                      onChange={(event) =>
                        setTeacherAnswers((previous) =>
                          previous.map((value, i) =>
                            i === index ? event.target.value : value,
                          ),
                        )
                      }
                    />
                  </label>
                ))}
                {answersLocked && live.error && (
                  <p className="muted">
                    Answers are locked for this attempt so a retry uses the same
                    responses.
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
                  (!decision || (decision === "answer" && !answer.trim()))) ||
                (custom &&
                  live.evidence !== null &&
                  (teacherAnswers.length !== live.missingInformation.length ||
                    teacherAnswers.some((value) => !value.trim())))
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
          <div className="live-run-notes">
            <span>Hosted demos share 20 live runs per day.</span>{" "}
            <span>Drafts and results disappear when you leave or refresh.</span>
          </div>
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
                {edited === null ? "AI-generated draft" : "AI draft edited"} ·{" "}
                {live.model} · Review before approving
              </p>
              {scenario === "booking" && !approved && (
                <p className="muted footnote">
                  Approving simulates a booking for{" "}
                  {tourBooking.session.className} on {tourBooking.session.date}{" "}
                  at {tourBooking.session.time}, {tourBooking.session.location}.
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
              {approved && custom && (
                <p className="muted">
                  Simulation complete. No email was sent and no studio records
                  were changed.
                </p>
              )}
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
            <SupportingEvidence evidence={live.evidence} showConversationLink />
          )}
        </section>
      </div>
    </>
  );
}
