import { useEffect, useRef, useState } from "react";
import { DraftEmailEditor } from "./DraftEmailEditor";
import { SupportingEvidence } from "./SupportingEvidence";
import { DemoQuestionAnswers } from "./DemoQuestionAnswers";
import { ReviewRequirementBadges } from "./Classification";
import type { useLiveDemo } from "./useLiveDemo";

export function DemoResponse({
  live,
  separateEvidence = false,
  savedAnswers = [],
  answersWereSubmitted = false,
  onAnswers,
  savedEdit,
  onEdit,
  onApproved,
}: {
  live: ReturnType<typeof useLiveDemo>;
  separateEvidence?: boolean;
  savedAnswers?: string[];
  answersWereSubmitted?: boolean;
  onAnswers?: (answers: string[], submitted: boolean) => void;
  savedEdit?: string | null;
  onEdit?: (body: string | null) => void;
  onApproved?: (
    approval: NonNullable<ReturnType<typeof useLiveDemo>["approval"]>,
    token: string,
  ) => void;
}) {
  const [teacherAnswers, setTeacherAnswers] = useState<string[]>(savedAnswers);
  const [edited, setEdited] = useState<string | null>(savedEdit ?? null);
  const [answersLocked, setAnswersLocked] = useState(answersWereSubmitted);
  const body = edited ?? live.draft ?? "";
  const booking = live.approval?.booking;
  const approved = Boolean(live.approval);
  const needsTeacherInput = live.reviewRequirements.includes("teacher_input");
  const [working, setWorking] = useState(false);
  const generating = useRef(false);
  const questionsAnswered = live.missingInformation.every((_, index) =>
    teacherAnswers[index]?.trim(),
  );
  useEffect(() => {
    if (live.draft && live.missingInformation.length)
      setTeacherAnswers(Array(live.missingInformation.length).fill(""));
  }, [live.draft]);
  async function generate() {
    if (generating.current) return;
    if (
      !separateEvidence &&
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
        if (
          !found ||
          found.automatic_approval ||
          found.missing_information?.length
        )
          return;
      } else if (!questionsAnswered) {
        return;
      }
      setAnswersLocked(true);
      onAnswers?.(teacherAnswers, true);
      const generated = await live.execute(
        "draft",
        live.missingInformation.map((_, index) => teacherAnswers[index]),
      );
      if (generated && !separateEvidence) setEdited(null);
    } finally {
      generating.current = false;
      setWorking(false);
    }
  }
  async function approve() {
    const result = await live.approve(body);
    if (result) onApproved?.(result, live.runToken.current);
  }
  async function applyTeacherAnswers() {
    if (!questionsAnswered) return;
    const result = await live.execute("revise", teacherAnswers);
    if (result) {
      setEdited(null);
      onEdit?.(null);
    }
  }
  return (
    <section className="panel" aria-labelledby="draft-heading">
      <DraftEmailEditor
        headingId="draft-heading"
        inputId={
          separateEvidence ? "walkthrough-response" : "live-review-response"
        }
        value={body}
        onChange={(reply) => {
          setEdited(reply);
          onEdit?.(reply);
        }}
        disabled={
          working ||
          Boolean(live.busy) ||
          approved ||
          live.bookingProposed ||
          (separateEvidence && !live.draft)
        }
        placeholder="Write a response or generate a draft."
        description={
          !live.draft
            ? "Generate a response based on the email and available studio information. Review it before approving."
            : undefined
        }
      />
      {!approved && (
        <ReviewRequirementBadges requirements={live.reviewRequirements} />
      )}
      {live.evidence && (!live.draft || needsTeacherInput) && (
        <DemoQuestionAnswers
          questions={live.missingInformation}
          answers={teacherAnswers}
          onChange={(index, answer) => {
            const answers = live.missingInformation.map((_, i) =>
              i === index ? answer : teacherAnswers[i] || "",
            );
            setTeacherAnswers(answers);
            onAnswers?.(answers, false);
          }}
          disabled={(!live.draft && answersLocked) || working}
        />
      )}
      {!live.draft && (
        <button
          className="button primary live-draft-generate"
          disabled={
            working ||
            Boolean(live.busy) ||
            Boolean(live.evidence && !questionsAnswered)
          }
          onClick={() =>
            void (separateEvidence && !live.evidence
              ? live.execute("evidence")
              : generate())
          }
        >
          {live.busy === "evidence" && separateEvidence
            ? "Finding evidence…"
            : working || live.busy
              ? "Generating draft…"
              : separateEvidence && !live.evidence
                ? "Find evidence"
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
            {edited === null ? "AI-generated draft" : "AI draft edited"} ·{" "}
            {live.model} · Review before approving
          </p>
          {live.bookingProposed && !approved && (
            <p className="muted footnote">
              Approval simulates the booking for the verified class in the
              draft.
            </p>
          )}
          {needsTeacherInput && (
            <>
              <p className="muted">
                Answer these teacher questions to update the draft before
                approving it.
              </p>
              <button
                className="button primary"
                disabled={!questionsAnswered || working || Boolean(live.busy)}
                onClick={() => void applyTeacherAnswers()}
              >
                {working || live.busy === "revise"
                  ? "Updating draft…"
                  : "Update draft"}
              </button>
            </>
          )}
          <button
            className="button primary"
            disabled={
              !body.trim() ||
              approved ||
              needsTeacherInput ||
              Boolean(live.busy)
            }
            onClick={() => void approve()}
          >
            {approved
              ? "Approved"
              : separateEvidence
                ? "Simulate approval"
                : "Approve response"}
          </button>
          {approved && !booking && (
            <p className="muted">
              Simulation complete. No email was sent and no studio records were
              changed.
            </p>
          )}
          {booking && (
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
                  {booking.session.className}
                </p>
                <dl className="live-booking-facts">
                  <div>
                    <dt>Student</dt>
                    <dd>{booking.student.name}</dd>
                  </div>
                  <div>
                    <dt>Date</dt>
                    <dd>{booking.session.date}</dd>
                  </div>
                  <div>
                    <dt>Time</dt>
                    <dd>{booking.session.time}</dd>
                  </div>
                  <div>
                    <dt>Location</dt>
                    <dd>{booking.session.location}</dd>
                  </div>
                </dl>
                <p className="live-booking-note">
                  Simulated booking only. No place was reserved and no email was
                  sent.
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
            onClick={() =>
              live.draft
                ? void approve()
                : separateEvidence && !live.evidence
                  ? void live.execute("evidence")
                  : void generate()
            }
          >
            Retry
          </button>
        </div>
      )}
      {live.evidence && (
        <SupportingEvidence evidence={live.evidence} showConversationLink />
      )}
    </section>
  );
}
