import { useEffect, useRef, useState } from "react";
import { request } from "./data";
import type { TourScenario } from "./tourData";

export function useLiveDemo(scenario: TourScenario) {
  const [evidence, setEvidence] = useState<string[] | null>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const [model, setModel] = useState("");
  const [busy, setBusy] = useState<"evidence" | "draft" | null>(null);
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

  async function execute(stage: "evidence" | "draft") {
    if (
      pending.current ||
      (stage === "evidence" && evidence) ||
      (stage === "draft" && draft)
    )
      return;
    pending.current = true;
    setBusy(stage);
    setError("");
    try {
      if (!runToken.current) {
        const run = await request<{ token: string }>("/api/public-demo/runs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scenario, request_id: requestId.current }),
        });
        if (!mounted.current) return;
        runToken.current = run.token;
      }
      const result = await request<{
        evidence?: string[];
        body?: string;
        model: string;
      }>(`/api/public-demo/${stage}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${runToken.current}`,
        },
        body: "{}",
      });
      if (!mounted.current) return;
      if (stage === "evidence" && result.evidence?.length)
        setEvidence(result.evidence);
      else if (stage === "draft" && result.body?.trim()) setDraft(result.body);
      else
        throw new Error(
          "The live service returned an empty result. Retry this step.",
        );
      setModel(result.model);
    } catch (caught) {
      if (mounted.current)
        setError(
          caught instanceof Error
            ? caught.message
            : "The live step could not complete.",
        );
    } finally {
      pending.current = false;
      if (mounted.current) setBusy(null);
    }
  }
  return { evidence, draft, model, busy, error, execute };
}
