import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  createConfirmation,
  type TourConfirmation,
  documentDraft,
  tourFixtures,
  tourSource,
  tourSteps,
  type TourScenario,
} from "./tourData";
import "./tour.css";
import { useLiveDemo } from "./useLiveDemo";

type Decision = "" | "answer" | "defer";
function useTourState(scenario: TourScenario, liveMode: boolean) {
  const live = useLiveDemo(scenario);
  const [step, setStep] = useState(0);
  const [body, setBody] = useState(
    liveMode ? "" : tourFixtures[scenario].draft,
  );
  const [decision, setDecision] = useState<Decision>("");
  const [answer, setAnswer] = useState("");
  const [applied, setApplied] = useState("");
  const [sourceOpen, setSourceOpen] = useState(false);
  const [confirmation, setConfirmation] = useState<TourConfirmation | null>(
    null,
  );
  const signature =
    decision === "answer" ? `answer:${answer.trim()}` : decision;
  const resolved =
    (!liveMode || live.draft !== null) &&
    (scenario === "booking" ||
      Boolean(
        signature &&
        signature === applied &&
        (decision === "defer" || answer.trim()),
      ));
  useEffect(() => {
    if (liveMode && live.draft !== null) {
      setBody(live.draft);
      setApplied("");
    }
  }, [liveMode, live.draft]);
  function updateDraft() {
    if (!decision || (decision === "answer" && !answer.trim())) return;
    setBody(
      documentDraft(
        decision,
        answer,
        liveMode ? live.draft || undefined : undefined,
      ),
    );
    setApplied(signature);
  }
  return {
    live,
    liveMode,
    step,
    setStep,
    body,
    setBody,
    decision,
    setDecision,
    answer,
    setAnswer,
    sourceOpen,
    setSourceOpen,
    confirmation,
    setConfirmation,
    resolved,
    updateDraft,
  };
}
const TourContext = createContext<ReturnType<typeof useTourState> | null>(null);
function TourProvider({
  scenario,
  liveMode,
  children,
}: {
  scenario: TourScenario;
  liveMode: boolean;
  children: ReactNode;
}) {
  const state = useTourState(scenario, liveMode);
  return <TourContext.Provider value={state}>{children}</TourContext.Provider>;
}
export function GuidedTour() {
  const [params] = useSearchParams();
  const scenario =
    params.get("scenario") === "document" ? "document" : "booking";
  const liveMode = params.get("mode") === "live";
  const [reset, setReset] = useState(0);
  return (
    <TourProvider
      key={`${scenario}-${liveMode}-${reset}`}
      scenario={scenario}
      liveMode={liveMode}
    >
      <TourContent
        scenario={scenario}
        reset={() => setReset((value) => value + 1)}
      />
    </TourProvider>
  );
}
function TourContent({
  scenario,
  reset,
}: {
  scenario: TourScenario;
  reset: () => void;
}) {
  const state = useContext(TourContext)!;
  const fixture = tourFixtures[scenario];
  const { live, liveMode } = state;
  const modeSuffix = liveMode ? "&mode=live" : "";
  const heading = useRef<HTMLHeadingElement>(null);
  const source = useRef<HTMLElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, [state.step]);
  useEffect(() => {
    if (state.sourceOpen) source.current?.focus();
  }, [state.sourceOpen]);
  function approve() {
    if (!state.resolved || !state.body.trim()) return;
    state.setConfirmation(createConfirmation(scenario, state.body));
    state.setStep(3);
  }
  return (
    <div className="guided-tour">
      <header className="page-heading">
        <div>
          <div className="eyebrow">TWO-MINUTE GUIDED DEMO</div>
          <h1>Take the teacher's seat.</h1>
          <p>
            Follow an email, inspect the evidence, and make a review decision.
          </p>
        </div>
      </header>
      <p className="notice" role="note">
        {liveMode
          ? "Live AI · Fixed fictional inputs · 10 shared demo runs per day. Find evidence and generate a draft with the buttons below. Booking remains simulated; no email is sent or studio records changed."
          : "Curated simulation · Fictional data · No live model calls. All changes stay in this tour and disappear when you leave or reload. No email is sent."}
      </p>
      <nav className="tour-scenarios" aria-label="Generation mode">
        <Link
          className="inline-link"
          aria-current={liveMode ? "page" : undefined}
          to={`/demo/tour?scenario=${scenario}&mode=live`}
        >
          Use live AI
        </Link>
        <Link
          className="inline-link"
          aria-current={!liveMode ? "page" : undefined}
          to={`/demo/tour?scenario=${scenario}`}
        >
          Use recorded demo
        </Link>
      </nav>
      <nav className="tour-scenarios" aria-label="Demo scenarios">
        <Link
          className={`button ${scenario === "booking" ? "primary" : "secondary"}`}
          to={`/demo/tour?scenario=booking${modeSuffix}`}
          aria-current={scenario === "booking" ? "page" : undefined}
        >
          Makeup booking
        </Link>
        <Link
          className={`button ${scenario === "document" ? "primary" : "secondary"}`}
          to={`/demo/tour?scenario=document${modeSuffix}`}
          aria-current={scenario === "document" ? "page" : undefined}
        >
          Document enquiry
        </Link>
      </nav>
      <ol className="tour-progress" aria-label="Tour progress">
        {tourSteps.map((label, index) => (
          <li
            key={label}
            aria-current={state.step === index ? "step" : undefined}
          >
            <span>{index + 1}</span>
            {label}
          </li>
        ))}
      </ol>
      <section className="panel tour-stage" aria-labelledby="tour-step-title">
        <div className="eyebrow">
          STEP {state.step + 1} OF 4 · {fixture.student}
        </div>
        <h2 id="tour-step-title" ref={heading} tabIndex={-1}>
          {state.step === 3
            ? scenario === "booking"
              ? "Class booked"
              : "Response approved"
            : tourSteps[state.step]}
        </h2>
        {state.step === 0 && (
          <>
            <p>
              {scenario === "booking"
                ? "A follow-up changes the requested day. Read both messages before reviewing the proposed booking."
                : "One email asks two questions. The selected document can answer only one."}
            </p>
            {fixture.messages.map((message) => (
              <article className="tour-message" key={message.sender}>
                <h3>{message.sender}</h3>
                <p>{message.body}</p>
              </article>
            ))}
          </>
        )}
        {state.step === 1 && (
          <>
            {liveMode ? (
              <>
                <p>
                  Click to ask AI to select supporting records and passages from
                  the fixed fictional catalog. This small demo does not search
                  your studio's database or run the full production RAG
                  pipeline.
                </p>
                <button
                  className="button primary"
                  disabled={Boolean(live.busy) || Boolean(live.evidence)}
                  onClick={() => live.execute("evidence")}
                >
                  {live.busy === "evidence"
                    ? "Finding evidence…"
                    : "Find supporting evidence"}
                </button>
                {live.busy === "evidence" && (
                  <p role="status">Finding supporting evidence…</p>
                )}
                {live.error && !live.evidence && (
                  <div role="alert">
                    <p>{live.error}</p>
                    <button
                      className="button secondary"
                      disabled={Boolean(live.busy)}
                      onClick={() => live.execute("evidence")}
                    >
                      Retry
                    </button>
                  </div>
                )}
              </>
            ) : (
              <p>
                These are prerecorded example checks, not checks against live
                studio records.
              </p>
            )}
            {(!liveMode || live.evidence) && (
              <>
                <ul className="tour-evidence">
                  {(liveMode ? live.evidence || [] : fixture.evidence).map(
                    (item) => (
                      <li key={item}>{item}</li>
                    ),
                  )}
                </ul>
                {scenario === "document" && (
                  <>
                    <div className="tour-columns">
                      <div>
                        <h3>
                          {liveMode
                            ? "Source guidance"
                            : "Document-grounded draft"}
                        </h3>
                        <p>
                          Wear comfortable clothes you can move in, such as
                          leggings and a fitted T-shirt. Socks are suitable for
                          your first class; ballet shoes are optional.
                        </p>
                        <p>Trial fee: teacher input needed.</p>
                      </div>
                      <div>
                        <h3>Supporting citation</h3>
                        <blockquote>{tourSource.quote}</blockquote>
                        <button
                          className="inline-link"
                          onClick={() => state.setSourceOpen(true)}
                          aria-expanded={state.sourceOpen}
                          aria-controls="tour-source"
                        >
                          Beginner clothing policy · Revision 1
                        </button>
                      </div>
                    </div>
                    {state.sourceOpen && (
                      <section
                        id="tour-source"
                        ref={source}
                        tabIndex={-1}
                        className="tour-source"
                        aria-label="Saved source revision"
                      >
                        <h3>Saved source revision</h3>
                        <p>
                          {tourSource.title} · Revision 1 · Fictional source
                        </p>
                        <pre>
                          {tourSource.text.slice(0, tourSource.start)}
                          <mark>
                            {tourSource.text.slice(
                              tourSource.start,
                              tourSource.end,
                            )}
                          </mark>
                          {tourSource.text.slice(tourSource.end)}
                        </pre>
                      </section>
                    )}
                  </>
                )}
              </>
            )}
          </>
        )}
        {state.step === 2 && (
          <>
            {liveMode && (
              <div className="tour-live-generation">
                <p>
                  Generate a fresh response from the selected fictional
                  evidence. Model output still needs teacher review.
                </p>
                <button
                  className="button primary"
                  disabled={
                    Boolean(live.busy) || Boolean(live.draft) || !live.evidence
                  }
                  onClick={() => live.execute("draft")}
                >
                  {live.busy === "draft"
                    ? "Generating draft…"
                    : "Generate draft"}
                </button>
                {live.busy === "draft" && (
                  <p role="status">Generating draft…</p>
                )}
                {live.error && (
                  <div role="alert">
                    <p>{live.error}</p>
                    <button
                      className="button secondary"
                      disabled={Boolean(live.busy)}
                      onClick={() => live.execute("draft")}
                    >
                      Retry
                    </button>
                  </div>
                )}
                {live.draft && (
                  <p className="muted">Generated live · {live.model}</p>
                )}
              </div>
            )}
            {scenario === "document" && (
              <fieldset
                className="tour-decision"
                disabled={liveMode && !live.draft}
              >
                <legend>What does a trial cost?</legend>
                <p>
                  {liveMode
                    ? "The source does not specify a fee. Supply a teacher fact or choose to confirm later, then update the draft. This adds your decision to the generated response and replaces any direct wording edits."
                    : "The source does not specify a fee. Supply a teacher fact or choose to confirm later, then update the draft. Updating replaces the response with the predetermined template and your decision."}
                </p>
                <label>
                  <input
                    type="radio"
                    name="fee-decision"
                    checked={state.decision === "answer"}
                    onChange={() => state.setDecision("answer")}
                  />{" "}
                  Provide an answer
                </label>
                <label>
                  <input
                    type="radio"
                    name="fee-decision"
                    checked={state.decision === "defer"}
                    onChange={() => state.setDecision("defer")}
                  />{" "}
                  Confirm later
                </label>
                {state.decision === "answer" && (
                  <div>
                    <label htmlFor="tour-fee-answer">Trial fee answer</label>
                    <textarea
                      id="tour-fee-answer"
                      value={state.answer}
                      onChange={(event) => state.setAnswer(event.target.value)}
                    />
                  </div>
                )}
                <button
                  className="button secondary"
                  onClick={state.updateDraft}
                  disabled={
                    !state.decision ||
                    (state.decision === "answer" && !state.answer.trim())
                  }
                >
                  Update draft
                </button>
                <p role="status">
                  {state.resolved
                    ? "Teacher decision applied. Review the final response below."
                    : "Teacher decision needed. Apply an answer or deferral before approval."}
                </p>
              </fieldset>
            )}
            <div className="tour-response">
              <label htmlFor="tour-final-response">Final response</label>
              <textarea
                id="tour-final-response"
                rows={9}
                value={state.body}
                onChange={(event) => state.setBody(event.target.value)}
              />
            </div>
            <p className="muted">
              Your edits are saved verbatim in the simulated outcome. No AI
              checks or validates your edited text.
            </p>
            {scenario === "booking" && (
              <p>
                No place is reserved yet. In the real workflow, approval
                rechecks capacity and eligibility before saving the response and
                booking atomically. This demo only simulates that outcome.
              </p>
            )}
            <button
              className="button primary"
              onClick={approve}
              disabled={!state.resolved || !state.body.trim()}
            >
              {scenario === "booking"
                ? "Simulate approval and booking"
                : "Simulate approval"}
            </button>
          </>
        )}
        {state.step === 3 && state.confirmation && (
          <Confirmation snapshot={state.confirmation} />
        )}
      </section>
      {state.step === 3 ? (
        <nav
          className="tour-controls tour-completion-actions"
          aria-label="Confirmation actions"
        >
          <button className="button secondary" onClick={() => state.setStep(2)}>
            Back to review
          </button>
          <button className="button secondary" onClick={reset}>
            Restart demo
          </button>
          <Link
            className="button primary"
            to={
              scenario === "booking"
                ? "/demo/tour?scenario=document"
                : "/demo/tour?scenario=booking"
            }
          >
            {scenario === "booking"
              ? "Try document enquiry"
              : "Try makeup booking"}
          </Link>
        </nav>
      ) : (
        <div className="tour-controls">
          <button
            className="button secondary"
            disabled={state.step === 0}
            onClick={() => state.setStep((value) => value - 1)}
          >
            Back
          </button>
          <button className="button secondary" onClick={reset}>
            Reset
          </button>
          {state.step < 2 && (
            <button
              className="button primary"
              disabled={liveMode && state.step === 1 && !live.evidence}
              onClick={() => state.setStep((value) => value + 1)}
            >
              Next
            </button>
          )}
        </div>
      )}
      <Link className="inline-link" to="/demo/reviews">
        Explore the read-only records
      </Link>
    </div>
  );
}

function Confirmation({ snapshot }: { snapshot: TourConfirmation }) {
  return (
    <div className="tour-confirmation">
      <span className="tour-simulation-badge">Simulation</span>
      {snapshot.kind === "booking" ? (
        <>
          <section
            className="tour-booking-card"
            aria-label="Booking confirmation"
          >
            <div className="eyebrow">CONFIRMED CLASS</div>
            <h3>{snapshot.session.className}</h3>
            <dl className="tour-booking-facts">
              <div>
                <dt>Student</dt>
                <dd>{snapshot.student.name}</dd>
              </div>
              <div>
                <dt>Date</dt>
                <dd>{snapshot.session.date}</dd>
              </div>
              <div>
                <dt>Time</dt>
                <dd>{snapshot.session.time}</dd>
              </div>
              <div>
                <dt>Location</dt>
                <dd>{snapshot.session.location}</dd>
              </div>
            </dl>
            <p className="tour-booking-status">
              ✓ Booking saved to the session roster — simulated.
            </p>
          </section>
          <section
            className="tour-database-update"
            aria-labelledby="tour-database-title"
          >
            <h3 id="tour-database-title">Database update</h3>
            <p>
              Approval adds Alex to this class session's student roster. The
              real application saves the roster and reviewed response together
              in PostgreSQL. This preview shows the simulated change only.
            </p>
            <div className="tour-roster-comparison">
              <Roster
                title="Before approval"
                members={snapshot.before}
                capacity={snapshot.session.capacity}
              />
              <Roster
                title="After approval"
                members={snapshot.after}
                capacity={snapshot.session.capacity}
                addedId={snapshot.student.id}
              />
            </div>
            <details className="tour-record-details">
              <summary>View saved record</summary>
              <p>
                Simulated record · <code>class_sessions.students</code> stores
                student UUIDs. Names above resolve from student profiles.
              </p>
              <dl>
                <dt>Session ID</dt>
                <dd>
                  <code>{snapshot.session.id}</code>
                </dd>
              </dl>
              <h4>Student membership before</h4>
              <pre>
                {JSON.stringify(
                  snapshot.before.map((member) => member.id),
                  null,
                  2,
                )}
              </pre>
              <h4>Student membership after</h4>
              <pre>
                {JSON.stringify(
                  snapshot.after.map((member) => member.id),
                  null,
                  2,
                )}
              </pre>
            </details>
          </section>
        </>
      ) : (
        <section
          className="tour-response-confirmed"
          aria-label="Response confirmation"
        >
          <h3>Reviewed response saved — simulated</h3>
          <p>
            Your reviewed text is retained below. This information-only enquiry
            creates no class booking.
          </p>
        </section>
      )}
      <details className="tour-approved-response">
        <summary>Approved response</summary>
        <p className="muted">Saved exactly as reviewed · simulated</p>
        <p className="tour-saved">{snapshot.approvedText}</p>
      </details>
      <section className="tour-email-status" aria-label="Email delivery">
        <h3>Email not sent</h3>
        <p>
          Approval saves the reviewed response; it does not send an email. No
          live studio records were changed by this simulation.
        </p>
      </section>
    </div>
  );
}

function Roster({
  title,
  members,
  capacity,
  addedId,
}: {
  title: string;
  members: { id: string; name: string }[];
  capacity: number;
  addedId?: string;
}) {
  const remaining = capacity - members.length;
  return (
    <section
      className={`tour-roster ${addedId ? "tour-roster-after" : ""}`}
      aria-label={title}
    >
      <h4>{title}</h4>
      <p>
        {members.length} of {capacity} places filled ·{" "}
        <strong>
          {remaining} {remaining === 1 ? "place" : "places"} remaining
        </strong>
      </p>
      <ul aria-label={title}>
        {members.map((member) => (
          <li
            key={member.id}
            className={member.id === addedId ? "tour-roster-added" : undefined}
          >
            {member.name}
            {member.id === addedId && <span>Added on approval</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}
