import { useEffect, useState } from "react";
import type { EnquiryAnswer, QuestionResolution, Run } from "./types";

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
  editable = false,
  busy = false,
  edits = {},
  onChange,
}: {
  run: Run;
  editable?: boolean;
  busy?: boolean;
  edits?: Record<string, QuestionResolution>;
  onChange?: (value: QuestionResolution) => void;
}) {
  const [showPrevious, setShowPrevious] = useState(false);
  useEffect(() => setShowPrevious(false), [run.id, run.revision]);
  const teacherQuestions = missingTeacherDecisions(run);
  const studentQuestions = (run.draft_details.answers || []).filter(
    (answer) => answer.status === "needs_student",
  );
  const applied = run.draft_details.question_resolutions || [];
  const previousQuestions = (run.draft_details.answers || []).filter(
    (answer) =>
      !!answer.question_id &&
      applied.some((item) => item.question_id === answer.question_id),
  );
  const hasNeeds = teacherQuestions.length > 0 || studentQuestions.length > 0;
  const visibleTeacherQuestions = showPrevious
    ? [...teacherQuestions, ...previousQuestions]
    : teacherQuestions;

  if (!hasNeeds && !showPrevious) {
    return editable && previousQuestions.length > 0 ? (
      <button
        className="text-button previous-answers-toggle"
        onClick={() => setShowPrevious(true)}
      >
        Edit previous teacher answers
      </button>
    ) : null;
  }

  return (
    <section className="panel input-needed" aria-label="Input needed">
      <h3>{hasNeeds ? "Input needed" : "Edit teacher answers"}</h3>
      {visibleTeacherQuestions.length > 0 && (
        <div className="input-needed-group">
          <h4>Needs teacher input</h4>
          <p className="muted">
            Add the studio facts or mark what you’ll confirm later, then update
            the draft before approval.
          </p>
          {visibleTeacherQuestions.map((answer, index) => {
            const questionId = answer.question_id;
            const current = applied.find(
              (item) => item.question_id === questionId,
            );
            const selected = (questionId && edits[questionId]) || current;
            return (
              <div
                className="enquiry-question"
                key={questionId || index + "-" + answer.question}
              >
                <h5>{answer.question}</h5>
                {current && (
                  <p className="muted">
                    {current.decision === "defer"
                      ? "Previously marked to confirm later"
                      : "Previous teacher answer"}
                  </p>
                )}
                {editable && !questionId && (
                  <p className="notice">
                    This older review needs an updated question checklist.
                    Select Update draft first.
                  </p>
                )}
                {editable && questionId ? (
                  <div className="question-resolution">
                    {selected?.decision !== "defer" && (
                      <label>
                        Your answer
                        <textarea
                          aria-label={"Answer for " + answer.question}
                          rows={3}
                          maxLength={4000}
                          value={selected?.answer || ""}
                          placeholder="Enter the studio fact for the copilot."
                          disabled={busy}
                          onChange={(event) =>
                            onChange?.({
                              question_id: questionId,
                              decision: "answer",
                              answer: event.target.value,
                            })
                          }
                        />
                      </label>
                    )}
                    <label className="question-defer">
                      <input
                        type="checkbox"
                        checked={selected?.decision === "defer"}
                        disabled={busy}
                        onChange={(event) =>
                          onChange?.({
                            question_id: questionId,
                            decision: event.target.checked ? "defer" : "answer",
                            answer: event.target.checked ? null : "",
                          })
                        }
                      />
                      I’ll confirm this later
                    </label>
                    {edits[questionId] && (
                      <small role="status">
                        Unapplied choice — update the draft to use it.
                      </small>
                    )}
                  </div>
                ) : (
                  <p className="muted">
                    The teacher needs to provide this studio fact.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
      {studentQuestions.length > 0 && (
        <div className="input-needed-group">
          <h4>Needs student input</h4>
          <p className="muted">
            Check that the response asks the student for these details. Approval
            can save that clarification reply without sending an email.
          </p>
          <ul>
            {studentQuestions.map((answer, index) => (
              <li key={answer.question_id || index}>{answer.question}</li>
            ))}
          </ul>
        </div>
      )}
      {editable && previousQuestions.length > 0 && (
        <button
          className="text-button previous-answers-toggle"
          onClick={() => setShowPrevious((value) => !value)}
        >
          {showPrevious
            ? "Hide previous teacher answers"
            : "Edit previous teacher answers"}
        </button>
      )}
    </section>
  );
}
