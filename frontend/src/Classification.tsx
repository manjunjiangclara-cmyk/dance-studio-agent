import type { RunStatus } from "./types";

const labels: Record<string, string> = {
  makeup: "Makeup",
  absence: "Session absence",
  enrolment: "Enrolment change",
  cancellation: "Enrolment cancellation",
  new_student_enquiry: "New student enquiry",
  general_enquiry: "General enquiry",
  unknown: "Unclear request",
};
function record(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}
function intents(routing: unknown): string[] {
  const value = record(routing)?.intents;
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}
export function IntentBadges({
  routing,
  showLabel = false,
}: {
  routing: unknown;
  showLabel?: boolean;
}) {
  const values = [...new Set(intents(routing))];
  if (!values.length) return null;
  return (
    <div className="intent-badges" aria-label="Classified intents">
      {showLabel && <span className="intent-label">Intent:</span>}
      {values.map((intent) => (
        <span className="intent-badge" key={intent}>
          {labels[intent] || intent.replaceAll("_", " ")}
        </span>
      ))}
    </div>
  );
}
export function ClassificationPanel({
  interpretation,
  status,
}: {
  interpretation: Record<string, unknown>;
  status: RunStatus;
}) {
  const routing = record(interpretation.routing);
  const flow = interpretation.flow;
  return (
    <section
      className="panel classification-panel"
      aria-labelledby="classification-title"
    >
      <h2 id="classification-title">Classification</h2>
      {!intents(routing).length ? (
        <p className="muted">
          {status === "running"
            ? "Classification pending."
            : "Classification was not recorded for this run."}
        </p>
      ) : (
        <>
          <div className="classification-overview">
            <IntentBadges routing={routing} showLabel />
            <dl className="classification-meta">
              <div>
                <dt>Workflow</dt>
                <dd>
                  {flow === "makeup"
                    ? "Makeup workflow"
                    : flow === "enquiry"
                      ? "Enquiry workflow"
                      : flow === "teacher_handoff"
                        ? "Teacher handling"
                        : "Not recorded"}
                </dd>
              </div>
              {typeof routing?.action === "string" && (
                <div>
                  <dt>Requested action</dt>
                  <dd>
                    {{
                      information_only: "Information only",
                      makeup_booking: "Makeup booking",
                      other_action: "Human action required",
                      unclear: "Needs human clarification",
                    }[routing.action] || "Not recorded"}
                  </dd>
                </div>
              )}
              <div>
                <dt>Clarification</dt>
                <dd>
                  {routing?.needs_clarification === true
                    ? "Needed"
                    : routing?.needs_clarification === false
                      ? "Not flagged by router"
                      : "Not recorded"}
                </dd>
              </div>
            </dl>
          </div>
          {typeof routing?.reason === "string" && routing.reason && (
            <div className="classification-reason">
              <h3>Why this classification</h3>
              <p>{routing.reason}</p>
            </div>
          )}
          {flow === "teacher_handoff" && (
            <p className="muted classification-note">
              A teacher must handle the requested action or clarify what is
              needed. Approving this reply saves the response only.
            </p>
          )}
        </>
      )}
    </section>
  );
}
