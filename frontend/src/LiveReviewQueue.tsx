import { Link } from "react-router-dom";
import { StudentEmailCard } from "./StudentEmailCard";
import { IntentBadges } from "./Classification";
import { DemoResponse } from "./DemoResponse";
import { useLiveDemo, type PublicDemoScenario } from "./useLiveDemo";

const cases: {
  scenario: PublicDemoScenario;
  name: string;
  studentId?: string;
  emailBody?: string;
  subject: string;
  email: string;
  description: string;
  category: string;
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
    category: "MAKEUP REQUEST",
    intent: "makeup",
    received: "2027-02-07",
    messageTimes: ["2027-02-07T10:00:00+11:00", "2027-02-07T10:05:00+11:00"],
  },
  {
    scenario: "document",
    name: "Jules Park",
    subject: "Questions about starting ballet",
    email: "jules@example.test",
    description: "Asks what to wear to a first ballet class.",
    category: "NEW STUDENT",
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
    category: "MAKEUP REQUEST",
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
    category: "CLASS ENQUIRY",
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

export function LiveReviewCases({
  dashboard = false,
}: {
  dashboard?: boolean;
}) {
  return (
    <div className="run-list">
      {cases
        .filter(
          (item) =>
            !dashboard ||
            item.scenario === "booking" ||
            item.scenario === "document",
        )
        .map((item) => (
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
              {dashboard && (
                <span className="dashboard-case-category">{item.category}</span>
              )}
              <strong>{dashboard ? item.name : item.subject}</strong>
              <span className="case-description">{item.description}</span>
              {!dashboard && (
                <IntentBadges routing={{ intents: [item.intent] }} />
              )}
            </div>
            {dashboard ? (
              <span className="dashboard-case-action">
                Explore example <span aria-hidden="true">→</span>
              </span>
            ) : (
              <span className="run-meta live-case-date">
                <time dateTime={item.received}>
                  {formatReceived(item.received)}
                </time>
              </span>
            )}
          </Link>
        ))}
    </div>
  );
}

export function LiveReviewDetail({
  scenario,
}: {
  scenario: PublicDemoScenario;
}) {
  const item = cases.find((entry) => entry.scenario === scenario)!;
  const live = useLiveDemo(scenario);
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
            From <span className="review-email-address">{item.email}</span> ·
            Received{" "}
            <time dateTime={item.received}>
              {formatReceived(item.received)}
            </time>
          </p>
          <IntentBadges routing={{ intents: [item.intent] }} />
        </div>
      </header>
      <div className="notice">
        <ul className="notice-list">
          <li>Drafts and results disappear when you leave or refresh.</li>
          <li>Hosted demos share 20 live runs per day.</li>
          <li>
            Approval is simulated: no email is sent and no studio records are
            changed.
          </li>
        </ul>
      </div>
      {live.messages ? (
        <StudentEmailCard
          name={item.name}
          messages={live.messages.map((message) => ({
            body: message.body,
            dateTime: message.occurred_at,
            time: formatTime(message.occurred_at),
          }))}
        />
      ) : (
        <p role={live.error ? "alert" : "status"}>
          {live.error || "Loading the example email…"}
        </p>
      )}
      <DemoResponse live={live} />
    </>
  );
}
