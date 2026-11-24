export const DEMO_DEFER = "I will confirm this information later.";

export function DemoQuestionAnswers({
  questions,
  answers,
  onChange,
  disabled,
}: {
  questions: string[];
  answers: string[];
  onChange: (index: number, answer: string) => void;
  disabled: boolean;
}) {
  return (
    <>
      {questions.map((question, index) => (
        <fieldset className="demo-question" key={question} disabled={disabled}>
          <legend>{question}</legend>
          <label>
            <input
              type="checkbox"
              checked={answers[index] === DEMO_DEFER}
              onChange={(event) =>
                onChange(index, event.target.checked ? DEMO_DEFER : "")
              }
            />{" "}
            Confirm later
          </label>
          {answers[index] !== DEMO_DEFER && (
            <label>
              {question} answer
              <textarea
                value={answers[index] || ""}
                maxLength={2000}
                onChange={(event) => onChange(index, event.target.value)}
              />
            </label>
          )}
        </fieldset>
      ))}
    </>
  );
}
