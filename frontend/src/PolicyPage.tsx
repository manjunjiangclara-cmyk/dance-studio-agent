import { useEffect, useState } from "react";
import { useBlocker } from "react-router-dom";
import { request } from "./data";

type Policy = {
  version: string;
  absence_notice_before_start: boolean;
  explanation: string;
  level_order: string[];
};
const example: Policy = {
  version: "Example",
  level_order: ["Level 1", "Level 2", "Level 3"],
  absence_notice_before_start: true,
  explanation:
    "Illustrative rule: an absence notice must arrive strictly before the session starts. This check alone does not establish makeup eligibility or reserve a place.",
};

export function PolicyPage({
  workspace,
  csrf,
}: {
  workspace: boolean;
  csrf: string;
}) {
  const [saved, setSaved] = useState<Policy>();
  const [draft, setDraft] = useState<Policy>();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const dirty =
    workspace && !!draft && JSON.stringify(draft) !== JSON.stringify(saved);
  const blocker = useBlocker(dirty);
  useEffect(() => {
    let active = true;
    setError("");
    (workspace ? request<Policy>("/api/v1/policy") : Promise.resolve(example))
      .then((value) => {
        if (active) {
          setSaved(value);
          setDraft(value);
        }
      })
      .catch((err) => {
        if (active) setError((err as Error).message);
      });
    return () => {
      active = false;
    };
  }, [workspace, attempt]);
  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (dirty) event.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);
  function change(patch: Partial<Policy>) {
    setDraft((current) => current && { ...current, ...patch });
    setMessage("");
  }
  async function save() {
    if (!workspace || !draft || busy) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const value = await request<Policy>("/api/v1/policy", {
        method: "PUT",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({
          ...draft,
          level_order: draft.level_order
            .map((level) => level.trim())
            .filter(Boolean),
        }),
      });
      setSaved(value);
      setDraft(value);
      setMessage("Policy saved. New AI runs will use these settings.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Rules</h2>
          <p>
            Set the rules used for new AI runs. Existing reviews keep their
            original policy snapshot.
          </p>
        </div>
      </div>
      {!workspace && (
        <div className="notice">
          Read-only example. Sign in to the owner workspace to update your
          studio policy.
        </div>
      )}
      {error && (
        <div className="notice error" role="alert">
          <p>{error}</p>
          {!draft && (
            <button
              className="button secondary"
              onClick={() => setAttempt((n) => n + 1)}
            >
              Try loading again
            </button>
          )}
        </div>
      )}
      {message && (
        <div className="notice" role="status">
          {message}
        </div>
      )}
      {!draft && !error && <p role="status">Loading policy…</p>}
      {draft && (
        <form
          className="panel policy-form"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <div className="knowledge-panel-heading">
            <h2>Studio rules</h2>
            <p>Settings used to check and explain responses.</p>
          </div>
          <fieldset disabled={!workspace || busy}>
            <label>
              Policy version
              <input
                required
                maxLength={100}
                value={draft.version}
                onChange={(event) => change({ version: event.target.value })}
              />
            </label>
            <label className="policy-toggle">
              <input
                type="checkbox"
                checked={draft.absence_notice_before_start}
                onChange={(event) =>
                  change({ absence_notice_before_start: event.target.checked })
                }
              />
              Require absence notice before the session starts
            </label>
            <label>
              Class levels, easiest to most difficult (one per line)
              <textarea
                rows={5}
                value={draft.level_order.join("\n")}
                onChange={(event) =>
                  change({ level_order: event.target.value.split("\n") })
                }
              />
              <small>
                Makeup suggestions require this order and recorded attendance.
              </small>
            </label>
            <label>
              Policy explanation
              <textarea
                required
                maxLength={10000}
                rows={8}
                value={draft.explanation}
                onChange={(event) =>
                  change({ explanation: event.target.value })
                }
              />
            </label>
          </fieldset>
          <p>
            The checkbox controls the absence timing check, and the level order
            controls class suitability checks. Use the explanation to describe
            these rules to the AI; it does not create additional automated
            eligibility checks.
          </p>
          {workspace && (
            <div className="button-row">
              <button
                className="button primary"
                disabled={
                  !dirty ||
                  busy ||
                  !draft.version.trim() ||
                  !draft.explanation.trim()
                }
              >
                {busy ? "Saving…" : "Save policy"}
              </button>
              <button
                type="button"
                className="button secondary"
                disabled={!dirty || busy}
                onClick={() => {
                  setDraft(saved);
                  setError("");
                  setMessage("");
                }}
              >
                Discard changes
              </button>
              {dirty && <span>Unsaved changes</span>}
            </div>
          )}
        </form>
      )}
      {blocker.state === "blocked" && (
        <div className="dialog-overlay">
          <div
            className="panel dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="policy-leave-title"
          >
            <h2 id="policy-leave-title">Leave without saving?</h2>
            <p>Your policy changes have not been saved.</p>
            <div className="button-row">
              <button
                className="button primary"
                autoFocus
                onClick={() => blocker.reset()}
              >
                Stay here
              </button>
              <button
                className="button secondary"
                onClick={() => blocker.proceed()}
              >
                Leave page
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
