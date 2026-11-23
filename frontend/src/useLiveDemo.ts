import { useEffect, useRef, useState } from "react";
import { ApiError, request } from "./data";
import type { ReviewRequirement } from "./types";

export type PublicDemoScenario = "booking" | "document" | "noah" | "riley";
interface DemoStudent {
  id: string;
  name: string;
}
interface DemoSession {
  id: string;
  className: string;
  date: string;
  time: string;
  location: string;
  capacity: number;
  students: DemoStudent[];
}
type Stage = "evidence" | "draft" | "revise" | "approve";
type DemoMessage = { id: string; body: string; occurred_at: string };
type Approval = {
  status: "approved_mock";
  revision: number;
  body: string;
  booking_simulated: boolean;
  booking_kind?: "trial" | "makeup";
  booking?: { student: DemoStudent; session: DemoSession };
};

export type WalkthroughRun = {
  requestId: string;
  student: string;
  email: string;
  previousToken?: string;
  autoCheck?: boolean;
};

export function useLiveDemo(input: PublicDemoScenario | WalkthroughRun) {
  const scenario = typeof input === "string" ? input : null;
  const [messages, setMessages] = useState<DemoMessage[] | null>(null);
  const [reviewRequirements, setReviewRequirements] = useState<
    ReviewRequirement[]
  >([]);
  const [evidence, setEvidence] = useState<string[] | null>(null);
  const [missingInformation, setMissingInformation] = useState<string[]>([]);
  const [draft, setDraft] = useState<string | null>(null);
  const [revision, setRevision] = useState<number | null>(null);
  const [bookingProposed, setBookingProposed] = useState(false);
  const [automaticApproval, setAutomaticApproval] = useState<Approval | null>(
    null,
  );
  const [approval, setApproval] = useState<Approval | null>(null);
  const [model, setModel] = useState("");
  const [busy, setBusy] = useState<Stage | null>(null);
  const [error, setError] = useState("");
  const runToken = useRef("");
  const requestId = useRef(crypto.randomUUID());
  const pending = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (!scenario) return;
    let active = true;
    void request<{ messages: DemoMessage[] }>(
      `/api/public-demo/cases/${scenario}`,
    )
      .then((result) => {
        if (active) setMessages(result.messages);
      })
      .catch(() => {
        if (active) setError("The fictional email could not be loaded.");
      });
    return () => {
      active = false;
    };
  }, [scenario]);

  function report(caught: unknown) {
    if (mounted.current) {
      setError(
        caught instanceof ApiError && caught.status === 0
          ? "Connection interrupted. Retry to recover this live step."
          : caught instanceof Error
            ? caught.message
            : "The live step could not complete.",
      );
    }
  }

  async function execute(
    stage: Exclude<Stage, "approve">,
    teacherAnswers: string[] = [],
  ) {
    if (
      pending.current ||
      (stage === "evidence" && evidence) ||
      (stage === "draft" && draft) ||
      (stage === "revise" && !draft)
    )
      return;
    pending.current = true;
    setBusy(stage);
    setError("");
    try {
      if (!runToken.current) {
        const run = await request<{ token: string }>(
          typeof input === "string"
            ? "/api/public-demo/runs"
            : "/api/public-demo/walkthrough/runs",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(
              typeof input === "string"
                ? { scenario: input, request_id: requestId.current }
                : {
                    request_id: input.requestId,
                    student: input.student,
                    email_body: input.email,
                    previous_token: input.previousToken,
                  },
            ),
          },
        );
        if (!mounted.current) return;
        runToken.current = run.token;
      }
      const result = await request<{
        evidence?: string[];
        missing_information?: string[];
        review_requirements?: ReviewRequirement[];
        body?: string;
        revision?: number;
        booking_proposed?: boolean;
        automatic_approval?: Approval;
        model: string;
      }>(`/api/public-demo/${stage}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${runToken.current}`,
        },
        body: JSON.stringify(
          stage === "draft" || stage === "revise"
            ? {
                teacher_answers: teacherAnswers,
                ...(stage === "revise" ? { revision } : {}),
              }
            : {},
        ),
      });
      if (!mounted.current) return;
      if (stage === "evidence" && Array.isArray(result.evidence)) {
        setEvidence(result.evidence);
        setMissingInformation(result.missing_information || []);
        if (result.automatic_approval)
          setAutomaticApproval(result.automatic_approval);
      } else if (
        (stage === "draft" || stage === "revise") &&
        result.body?.trim() &&
        result.revision
      ) {
        setDraft(result.body);
        setRevision(result.revision);
        setBookingProposed(Boolean(result.booking_proposed));
        setMissingInformation(result.missing_information || []);
      } else {
        throw new Error(
          "The live service returned an empty result. Retry this step.",
        );
      }
      setReviewRequirements(result.review_requirements || []);
      setModel(result.model);
      return result;
    } catch (caught) {
      report(caught);
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(null);
    }
  }

  async function approve(body: string) {
    if (pending.current || !revision || approval) return;
    pending.current = true;
    setBusy("approve");
    setError("");
    try {
      const result = await request<Approval>("/api/public-demo/approve", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${runToken.current}`,
        },
        body: JSON.stringify({ revision, body }),
      });
      if (!mounted.current) return;
      if (result.status !== "approved_mock")
        throw new Error("The simulated approval could not be verified.");
      setApproval(result);
      return result;
    } catch (caught) {
      report(caught);
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(null);
    }
  }

  return {
    messages,
    evidence,
    missingInformation,
    reviewRequirements,
    draft,
    bookingProposed,
    approval,
    automaticApproval,
    model,
    busy,
    error,
    execute,
    approve,
    runToken,
  };
}
