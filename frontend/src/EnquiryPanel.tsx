import { Link } from "react-router-dom";
import type { EnquiryAnswer, QuestionResolution, Run } from "./types";

const statuses = {
  answered: "Answered",
  needs_student: "Needs student clarification",
  needs_teacher: "Needs teacher input",
};

export function needsTeacherDecision(run: Run, answer: EnquiryAnswer) {
  return (
    answer.status === "needs_teacher" ||
    (!!answer.question_id &&
      (run.draft_details.required_question_ids || []).includes(
        answer.question_id,
      ))
  );
}

export function missingTeacherDecisions(run: Run) {
  const applied = run.draft_details.question_resolutions || [];
  return (run.draft_details.answers || []).filter(
    (answer) =>
      needsTeacherDecision(run, answer) &&
      (!answer.question_id ||
        !applied.some((item) => item.question_id === answer.question_id)),
  );
}

export function EnquiryPanel({
  run,
  base,
  editable = false,
  busy = false,
  edits = {},
  onChange,
}: {
  run: Run;
  base: string;
  editable?: boolean;
  busy?: boolean;
  edits?: Record<string, QuestionResolution>;
  onChange?: (value: QuestionResolution) => void;
}) {
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
      {editable && (
        <p>
          After entering answers, select Update draft to have the agent create a
          new draft for your review.
        </p>
      )}
      {answers.map((answer, index) => {
        const questionId = answer.question_id;
        const applied = (run.draft_details.question_resolutions || []).find(
          (item) => item.question_id === questionId,
        );
        const selected = (questionId && edits[questionId]) || applied;
        const needsDecision = needsTeacherDecision(run, answer);
        return (
          <div
            className="enquiry-question"
            key={questionId || `${index}-${answer.question}`}
          >
            <h3>{answer.question}</h3>
            <span className={`enquiry-status ${answer.status}`}>
              {statuses[answer.status]}
            </span>
            <p>{answer.answer}</p>
            {applied && (
              <p className="muted resolution-applied">
                {applied.decision === "answer"
                  ? "Teacher answer applied"
                  : "Confirm later applied · still awaiting confirmation"}
              </p>
            )}
            {editable && needsDecision && !questionId && (
              <p className="notice">
                This older review needs an updated question checklist. Select
                Update draft first.
              </p>
            )}
            {editable && needsDecision && questionId && (
              <fieldset className="question-resolution" disabled={busy}>
                <legend>Teacher decision</legend>
                <label>
                  <input
                    type="radio"
                    name={`resolution-${questionId}`}
                    aria-label={`Provide answer for ${answer.question}`}
                    checked={selected?.decision === "answer"}
                    onChange={() =>
                      onChange?.({
                        question_id: questionId,
                        decision: "answer",
                        answer: selected?.answer || "",
                      })
                    }
                  />
                  Provide answer
                </label>
                <label>
                  <input
                    type="radio"
                    name={`resolution-${questionId}`}
                    aria-label={`Confirm later for ${answer.question}`}
                    checked={selected?.decision === "defer"}
                    onChange={() =>
                      onChange?.({
                        question_id: questionId,
                        decision: "defer",
                        answer: null,
                      })
                    }
                  />
                  Confirm later
                </label>
                {selected?.decision === "answer" && (
                  <label>
                    Answer for the student
                    <textarea
                      aria-label={`Answer for ${answer.question}`}
                      rows={3}
                      maxLength={4000}
                      value={selected.answer || ""}
                      placeholder="Write the answer you want to give the student."
                      onChange={(event) =>
                        onChange?.({ ...selected, answer: event.target.value })
                      }
                    />
                  </label>
                )}
                {edits[questionId] && (
                  <small role="status">
                    Unapplied choice — update the draft to send it to the agent.
                  </small>
                )}
              </fieldset>
            )}
            {!!answer.references.length && (
              <div
                className="reference-list"
                aria-label="Supporting references"
              >
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
                      {reference.startsWith("teacher_answer:")
                        ? "Teacher-provided answer"
                        : reference.startsWith("teacher_deferral:")
                          ? "Explicit teacher deferral"
                          : reference === "teacher_feedback"
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
        );
      })}
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
