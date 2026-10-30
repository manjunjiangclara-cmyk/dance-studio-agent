import { Link } from "react-router-dom";
import type { Run } from "./types";

const statuses = {
  answered: "Answered",
  needs_student: "Needs student clarification",
  needs_teacher: "Needs teacher input",
};

export function EnquiryPanel({ run, base }: { run: Run; base: string }) {
  const answers = run.draft_details.answers || [];
  const actions = Array.isArray(run.interpretation.requested_actions)
    ? run.interpretation.requested_actions.filter(
        (action): action is string => typeof action === "string",
      )
    : [];
  if (!answers.length && !actions.length) return null;
  return (
    <section
      className="panel context-card enquiry-panel"
      aria-labelledby="enquiry-title"
    >
      <h2 id="enquiry-title">Enquiry checklist</h2>
      {answers.map((answer, index) => (
        <div className="enquiry-question" key={`${index}-${answer.question}`}>
          <h3>{answer.question}</h3>
          <span className={`enquiry-status ${answer.status}`}>
            {statuses[answer.status]}
          </span>
          <p>{answer.answer}</p>
          {!!answer.references.length && (
            <div className="reference-list" aria-label="Supporting references">
              {answer.references.map((reference) =>
                reference.startsWith("session:") ? (
                  <Link
                    key={reference}
                    to={`${base}/timetable?session=${encodeURIComponent(reference.slice(8))}`}
                  >
                    View session
                  </Link>
                ) : (
                  <span key={reference}>
                    {reference === "teacher_feedback"
                      ? "Teacher revision feedback"
                      : reference.startsWith("class:")
                        ? "Class timetable"
                        : reference.startsWith("location:")
                          ? "Studio location"
                          : reference.startsWith("policy:")
                            ? "Studio policy"
                            : "Studio record"}
                  </span>
                ),
              )}
            </div>
          )}
        </div>
      ))}
      {!!actions.length && (
        <div className="enquiry-actions">
          <h3>Actions for the teacher</h3>
          <ul>
            {actions.map((action, index) => (
              <li key={index}>{action}</li>
            ))}
          </ul>
          <p className="muted">
            These actions have not been performed. Approval saves the reply
            only.
          </p>
        </div>
      )}
    </section>
  );
}
