import { useEffect, useRef, useState } from "react";
import { useBlocker, useSearchParams } from "react-router-dom";
import { ApiError, request } from "./data";
import "./documents.css";

type Summary = {
  id: string;
  title: string;
  filename: string;
  updated_at: string;
  current_revision: number;
  archived_at?: string | null;
  byte_size: number;
  sha256: string;
  hash_origin: string;
  ingestion_status: string;
  effective_from: string | null;
  effective_to: string | null;
  duplicates?: { id: string; title: string }[];
};
type Revision = Summary & { revision: number; created_at: string };
type Activation = {
  status: "disabled" | "preparing" | "enabled" | "failed";
  error: string | null;
};
type Draft = {
  title: string;
  filename: string;
  content?: string;
  effective_from: string;
  effective_to: string;
};
type Preview = {
  revision: number;
  content: string;
  offset: number;
  next_offset: number | null;
  total_characters: number;
};
const example: Summary & { content: string } = {
  id: "example",
  title: "Studio welcome",
  filename: "welcome.md",
  content: "# Welcome\n\nThis is an illustrative studio document.",
  updated_at: "2026-01-01T00:00:00Z",
  current_revision: 1,
  byte_size: 59,
  sha256: "",
  hash_origin: "stored_text_utf8",
  ingestion_status: "ready",
  effective_from: null,
  effective_to: null,
};
const makeDraft = (value: Summary, content?: string): Draft => ({
  title: value.title,
  filename: value.filename,
  content,
  effective_from: value.effective_from || "",
  effective_to: value.effective_to || "",
});
const root = "/api/v1/documents";

export function DocumentsPage({
  workspace,
  csrf,
}: {
  workspace: boolean;
  csrf: string;
}) {
  const [searchParams] = useSearchParams();
  const loadSequence = useRef(0);
  const linkedDocument = workspace ? searchParams.get("document") : null;
  const linkedRevision = searchParams.get("revision");
  const linkedOffset = searchParams.get("offset");
  const [showArchived, setShowArchived] = useState(false);
  const [documents, setDocuments] = useState<Summary[]>();
  const [saved, setSaved] = useState<Summary>();
  const [original, setOriginal] = useState<Draft>();
  const [draft, setDraft] = useState<Draft>();
  const [file, setFile] = useState<File>();
  const [fileText, setFileText] = useState<string>();
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [preview, setPreview] = useState<Preview>();
  const [previousOffsets, setPreviousOffsets] = useState<number[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [activation, setActivation] = useState<Activation>();
  const [activationError, setActivationError] = useState("");
  const [activationBusy, setActivationBusy] = useState(false);
  const [activationRefresh, setActivationRefresh] = useState(0);
  const dirty =
    workspace &&
    !!draft &&
    (!!file || JSON.stringify(draft) !== JSON.stringify(original));
  const blocker = useBlocker(dirty);

  useEffect(() => {
    let active = true;
    (workspace
      ? request<Summary[]>(`${root}?archived=${showArchived}`)
      : Promise.resolve([example])
    )
      .then((value) => {
        if (active) setDocuments(value);
      })
      .catch((err) => {
        if (active) setError((err as Error).message);
      });
    return () => {
      active = false;
    };
  }, [workspace, attempt, showArchived]);
  useEffect(() => {
    if (!workspace || !saved) {
      setActivation(undefined);
      return;
    }
    let active = true;
    let timer: number | undefined;
    setActivation(undefined);
    setActivationError("");
    async function refresh() {
      try {
        const value = await request<Activation>(
          `${root}/${saved!.id}/answer-activation`,
        );
        if (!active) return;
        setActivation(value);
        setActivationError("");
        if (value.status === "preparing")
          timer = window.setTimeout(refresh, 3000);
      } catch (err) {
        if (active) setActivationError((err as Error).message);
      }
    }
    void refresh();
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [workspace, saved?.id, saved?.current_revision, activationRefresh]);
  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (dirty) event.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  function fail(err: unknown) {
    setError((err as Error).message);
    setConflict(err instanceof ApiError && err.status === 409);
  }
  async function loadDocument(
    id: string,
    target?: { revision: number; offset: number },
    sequence = ++loadSequence.current,
  ) {
    const value = workspace
      ? await request<Summary>(`${root}/${id}/metadata`)
      : example;
    const [history, content] = await Promise.all([
      workspace
        ? request<Revision[]>(`${root}/${id}/revisions`)
        : Promise.resolve([]),
      !target && value.byte_size <= 1_000_000
        ? workspace
          ? request<{ content: string; current_revision: number }>(
              `${root}/${id}`,
            )
          : Promise.resolve(example)
        : Promise.resolve(undefined),
    ]);
    if (content && content.current_revision !== value.current_revision) {
      throw new ApiError(
        "The document changed while loading. Reload its current version.",
        409,
      );
    }
    if (target && !history.some((item) => item.revision === target.revision))
      throw new Error("The cited document revision is no longer available.");
    const first = workspace
      ? await request<Preview>(
          `${root}/${id}/revisions/${target?.revision ?? value.current_revision}/preview?offset=${target?.offset ?? 0}`,
        )
      : {
          revision: 1,
          content: example.content,
          offset: 0,
          next_offset: null,
          total_characters: example.content.length,
        };
    if (sequence !== loadSequence.current) return;
    const next = makeDraft(value, content?.content);
    setSaved(value);
    setOriginal(target ? undefined : next);
    setDraft(target ? undefined : next);
    setFile(undefined);
    setFileText(undefined);
    setRevisions(history);
    setPreview(first);
    setPreviousOffsets([]);
    setConflict(false);
  }
  useEffect(() => {
    const sequence = ++loadSequence.current;
    setBusy(false);
    if (!linkedDocument) return;
    if (dirty) {
      setError(
        "Save or discard your document edits before opening this citation.",
      );
      return;
    }
    close();
    const revision = Number(linkedRevision);
    const offset = Number(linkedOffset);
    if (
      !linkedRevision ||
      !linkedOffset ||
      !Number.isSafeInteger(revision) ||
      revision < 1 ||
      !Number.isSafeInteger(offset) ||
      offset < 0
    ) {
      setError("This document citation link is invalid.");
      return;
    }
    setBusy(true);
    setError("");
    void loadDocument(linkedDocument, { revision, offset }, sequence)
      .catch((error) => {
        if (sequence === loadSequence.current) fail(error);
      })
      .finally(() => {
        if (sequence === loadSequence.current) setBusy(false);
      });
  }, [linkedDocument, linkedRevision, linkedOffset]);
  useEffect(() => {
    if (linkedDocument && preview)
      document.getElementById("revision-preview")?.scrollIntoView();
  }, [linkedDocument, preview?.revision, preview?.offset]);
  async function selectDocument(id: string) {
    if (
      dirty &&
      !window.confirm("Discard unsaved changes and load the current version?")
    )
      return;
    const sequence = ++loadSequence.current;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await loadDocument(id, undefined, sequence);
    } catch (err) {
      if (sequence === loadSequence.current) fail(err);
    } finally {
      if (sequence === loadSequence.current) setBusy(false);
    }
  }
  async function chooseFile(selected?: File, newDocument = false) {
    if (!selected || busy) return;
    setBusy(true);
    try {
      if (!/\.(txt|md)$/i.test(selected.name))
        throw new Error("Choose a .txt or .md file.");
      if (selected.size > 10_000_000)
        throw new Error("Documents must be at most 10 MB.");
      if (selected.size === 0)
        throw new Error("Document text cannot be blank.");
      // Large files go directly to multipart upload; only small files enter the editor.
      const content =
        selected.size <= 1_000_000
          ? new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(
              await selected.arrayBuffer(),
            )
          : undefined;
      if (content?.includes("\0"))
        throw new Error("The file must contain text without NUL.");
      if (newDocument) {
        setSaved(undefined);
        setOriginal(undefined);
        setPreview(undefined);
        setRevisions([]);
      }
      setDraft((current) => ({
        title:
          (!newDocument && current?.title) ||
          selected.name.replace(/\.(txt|md)$/i, ""),
        filename: selected.name,
        content,
        effective_from: (!newDocument && current?.effective_from) || "",
        effective_to: (!newDocument && current?.effective_to) || "",
      }));
      setFile(selected);
      setFileText(content);
      setError("");
      setMessage("");
      setConflict(false);
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }
  async function save() {
    if (!workspace || !draft || busy || activationBusy || saved?.archived_at)
      return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const metadata = {
        title: draft.title,
        effective_from: draft.effective_from || null,
        effective_to: draft.effective_to || null,
        ...(saved ? { expected_revision: saved.current_revision } : {}),
      };
      let value: Summary;
      if (file) {
        const body = new FormData();
        for (const [key, item] of Object.entries(metadata))
          if (item !== null) body.set(key, String(item));
        const outgoing =
          draft.content !== undefined && draft.content !== fileText
            ? new File([draft.content], draft.filename, { type: "text/plain" })
            : file;
        if (outgoing.size > 10_000_000)
          throw new Error("Documents must be at most 10 MB.");
        body.set("file", outgoing);
        value = await request<Summary>(
          saved ? `${root}/${saved.id}/upload` : `${root}/upload`,
          {
            method: saved ? "PUT" : "POST",
            headers: { "X-CSRF-Token": csrf },
            body,
          },
        );
      } else if (saved) {
        const textChanged = draft.content !== original?.content;
        value = await request<Summary>(
          `${root}/${saved.id}/${textChanged ? "text" : "metadata"}`,
          {
            method: textChanged ? "PUT" : "PATCH",
            headers: {
              "Content-Type": "application/json",
              "X-CSRF-Token": csrf,
            },
            body: JSON.stringify(
              textChanged
                ? {
                    ...metadata,
                    filename: draft.filename,
                    content: draft.content,
                  }
                : metadata,
            ),
          },
        );
      } else {
        throw new Error("Choose a file first.");
      }
      // Clear dirty state only after the write succeeds; failed requests retain all local edits.
      setDocuments((current) => [
        value,
        ...(current || []).filter((item) => item.id !== value.id),
      ]);
      setSaved(value);
      setFile(undefined);
      setFileText(undefined);
      const next = makeDraft(value, draft.content);
      setOriginal(next);
      setDraft(next);
      setConflict(false);
      setMessage(
        saved
          ? "Document saved and approved. The previous revision is no longer used. Check preparation status below."
          : "Document saved. Uploading does not enable it for answers.",
      );
      setActivationRefresh((value) => value + 1);
      try {
        await loadDocument(value.id);
      } catch {
        setError(
          "Document saved, but its preview could not be refreshed. Reload the current version.",
        );
      }
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }
  async function changeActivation(method: "POST" | "DELETE") {
    if (!saved || activationBusy || busy || dirty || saved.archived_at) return;
    setActivationBusy(true);
    setActivationError("");
    try {
      await request<Activation>(`${root}/${saved.id}/answer-activation`, {
        method,
        headers: { "X-CSRF-Token": csrf },
      });
      setActivationRefresh((value) => value + 1);
    } catch (err) {
      setActivationError((err as Error).message);
    } finally {
      setActivationBusy(false);
    }
  }
  async function remove() {
    if (
      !saved ||
      busy ||
      activationBusy ||
      !!saved.archived_at ||
      !window.confirm(
        `Archive “${saved.title}”? It will stop being used for answers. Saved revisions remain available for historical citations.${dirty ? " Unsaved changes will be discarded." : ""}`,
      )
    )
      return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await request(`${root}/${saved.id}/archive`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrf, "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: saved.current_revision }),
      });
      setDocuments((current) =>
        current?.filter((item) => item.id !== saved.id),
      );
      close();
      setMessage("Document archived. It is no longer used for answers.");
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }
  function close() {
    setSaved(undefined);
    setOriginal(undefined);
    setDraft(undefined);
    setFile(undefined);
    setPreview(undefined);
    setRevisions([]);
    setConflict(false);
  }
  async function loadPreview(
    revision: number,
    offset = 0,
    direction: "next" | "previous" | "revision" = "revision",
  ) {
    if (!saved) return;
    const sequence = ++loadSequence.current;
    setBusy(true);
    setError("");
    try {
      const value = await request<Preview>(
        `${root}/${saved.id}/revisions/${revision}/preview?offset=${offset}`,
      );
      if (sequence !== loadSequence.current) return;
      setPreviousOffsets((current) =>
        direction === "next"
          ? [...current, preview?.offset || 0]
          : direction === "previous"
            ? current.slice(0, -1)
            : [],
      );
      setPreview(value);
    } catch (err) {
      if (sequence === loadSequence.current) fail(err);
    } finally {
      if (sequence === loadSequence.current) setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Documents</h2>
          <p>
            Manage studio reference material. Uploading does not enable a
            document for answers.
          </p>
        </div>
      </div>
      {!workspace && (
        <div className="notice">
          Read-only example. Sign in to manage your studio documents.
        </div>
      )}
      {error && (
        <div className="notice error" role="alert">
          {error}
          {!documents && (
            <button
              className="button secondary"
              onClick={() => setAttempt((n) => n + 1)}
            >
              Try loading again
            </button>
          )}
          {saved && conflict && (
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => void selectDocument(saved.id)}
            >
              Reload current version
            </button>
          )}
        </div>
      )}
      {message && (
        <div className="notice" role="status">
          {message}
        </div>
      )}
      {!documents && !error && <p role="status">Loading documents…</p>}
      {documents && (
        <section className="panel policy-form">
          <h2>Document library</h2>
          {workspace && (
            <label>
              <input
                type="checkbox"
                checked={showArchived}
                disabled={busy || activationBusy}
                onChange={(event) => {
                  if (dirty && !window.confirm("Discard unsaved changes?"))
                    return;
                  close();
                  setDocuments(undefined);
                  setShowArchived(event.target.checked);
                }}
              />
              Show archived documents
            </label>
          )}
          {documents.length === 0 ? (
            <p>
              {showArchived
                ? "No archived documents."
                : "No documents yet. Upload a text or Markdown file to get started."}
            </p>
          ) : (
            <ul className="document-list">
              {documents.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className="inline-link"
                    disabled={busy}
                    onClick={() => void selectDocument(item.id)}
                  >
                    {item.title}
                  </button>
                  <span>
                    {" "}
                    · Revision {item.current_revision} ·{" "}
                    {item.byte_size.toLocaleString()} bytes · Updated{" "}
                    {new Date(item.updated_at).toLocaleDateString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {workspace && !showArchived && (
            <label>
              Upload a document (.txt or .md, up to 10 MB)
              <input
                type="file"
                accept=".txt,.md,text/plain,text/markdown"
                disabled={busy}
                onChange={(event) => {
                  const selected = event.target.files?.[0];
                  if (
                    selected &&
                    (!dirty || window.confirm("Discard unsaved changes?"))
                  )
                    void chooseFile(selected, true);
                  event.target.value = "";
                }}
              />
            </label>
          )}
        </section>
      )}
      {draft && (
        <form
          className="panel policy-form"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <h2>{saved ? "Document details" : "New document"}</h2>
          {saved && (
            <p>
              Revision {saved.current_revision} ·{" "}
              {saved.byte_size.toLocaleString()} bytes ·{" "}
              {saved.ingestion_status === "ready"
                ? "Ingestion complete"
                : "Needs correction"}
              .
            </p>
          )}
          {workspace && saved && !saved.archived_at && (
            <section aria-label="Answers activation" className="notice">
              <h3>Use for answers</h3>
              <p>
                Saving changes approves the new revision and starts preparation.
                The previous revision stops being used immediately. Preparation
                may incur embedding API costs. Answers remain drafts for teacher
                review.
              </p>
              {!activation && !activationError && (
                <p role="status">Loading answer status…</p>
              )}
              {activation && (
                <p role="status">
                  {activation.status === "disabled" &&
                    "Not enabled for answers."}
                  {activation.status === "preparing" &&
                    "Preparing document for answers…"}
                  {activation.status === "enabled" && "Enabled for answers."}
                  {activation.status === "failed" &&
                    `Preparation failed${activation.error ? `: ${activation.error}` : "."}`}
                </p>
              )}
              {activationError && <p role="alert">{activationError}</p>}
              {dirty && (
                <p>Save or discard changes before changing answer status.</p>
              )}
              {activation && (
                <button
                  type="button"
                  className="button secondary"
                  disabled={busy || activationBusy || dirty}
                  onClick={() =>
                    void changeActivation(
                      activation.status === "enabled" ||
                        activation.status === "preparing"
                        ? "DELETE"
                        : "POST",
                    )
                  }
                >
                  {activation.status === "enabled"
                    ? "Disable for answers"
                    : activation.status === "preparing"
                      ? "Cancel preparation"
                      : activation.status === "failed"
                        ? "Retry preparation"
                        : "Enable for answers"}
                </button>
              )}
              {!activation && activationError && (
                <button
                  type="button"
                  className="button secondary"
                  onClick={() => setActivationRefresh((value) => value + 1)}
                >
                  Retry loading status
                </button>
              )}
            </section>
          )}
          {saved?.ingestion_status === "needs_correction" && (
            <p className="notice">
              This existing document is blank. Replace its file or edit its text
              to correct it.
            </p>
          )}
          {!!saved?.duplicates?.length && (
            <p className="notice">
              Same content as:{" "}
              {saved.duplicates.map((item) => item.title).join(", ")}. Each
              document is kept separately.
            </p>
          )}
          {saved?.archived_at && (
            <p className="notice">
              Archived document. Read-only and excluded from answers.
            </p>
          )}
          <fieldset
            disabled={
              !workspace || busy || activationBusy || !!saved?.archived_at
            }
          >
            <label>
              Title
              <input
                required
                maxLength={200}
                value={draft.title}
                onChange={(event) =>
                  setDraft({ ...draft, title: event.target.value })
                }
              />
            </label>
            <p>
              File: {draft.filename}
              {file ? ` · ${file.size.toLocaleString()} bytes selected` : ""}
            </p>
            <div className="document-dates">
              <label>
                Effective from
                <input
                  type="date"
                  value={draft.effective_from}
                  onChange={(event) =>
                    setDraft({ ...draft, effective_from: event.target.value })
                  }
                />
              </label>
              <label>
                Effective to
                <input
                  type="date"
                  min={draft.effective_from || undefined}
                  value={draft.effective_to}
                  onChange={(event) =>
                    setDraft({ ...draft, effective_to: event.target.value })
                  }
                />
              </label>
            </div>
            {workspace && saved && (
              <label>
                Replace file
                <input
                  type="file"
                  accept=".txt,.md,text/plain,text/markdown"
                  onChange={(event) => {
                    void chooseFile(event.target.files?.[0]);
                    event.target.value = "";
                  }}
                />
              </label>
            )}
            {draft.content !== undefined ? (
              <label>
                Document text
                <textarea
                  rows={14}
                  value={draft.content}
                  onChange={(event) =>
                    setDraft({ ...draft, content: event.target.value })
                  }
                />
              </label>
            ) : (
              <p>
                Files larger than 1 MB use a paginated preview. Replace the file
                to change its text.
              </p>
            )}
          </fieldset>
          {saved?.sha256 && (
            <details>
              <summary>Source integrity</summary>
              <p className="document-hash">SHA-256: {saved.sha256}</p>
              <p>
                {saved.hash_origin === "upload_bytes"
                  ? "Hash of the original uploaded bytes."
                  : "Hash reconstructed from stored UTF-8 text."}
              </p>
            </details>
          )}
          {workspace && !saved?.archived_at && (
            <div className="button-row">
              <button
                className="button primary"
                disabled={
                  !dirty || busy || activationBusy || !draft.title.trim()
                }
              >
                {busy
                  ? "Working…"
                  : saved
                    ? "Save and approve"
                    : "Save document"}
              </button>
              <button
                type="button"
                className="button secondary"
                disabled={busy}
                onClick={() => {
                  if (!dirty || window.confirm("Discard unsaved changes?"))
                    close();
                }}
              >
                Close
              </button>
              {saved && (
                <button
                  type="button"
                  className="button secondary"
                  disabled={busy || activationBusy}
                  onClick={() => void remove()}
                >
                  Archive document
                </button>
              )}
              {dirty && <span>Unsaved changes</span>}
            </div>
          )}
        </form>
      )}
      {saved && preview && (
        <section
          className="panel policy-form"
          aria-label="Revision preview"
          id="revision-preview"
        >
          <h2>Saved revision preview · {saved.title}</h2>
          {revisions.length > 0 && (
            <label>
              Revision
              <select
                disabled={busy}
                value={preview.revision}
                onChange={(event) =>
                  void loadPreview(Number(event.target.value))
                }
              >
                {revisions.map((item) => (
                  <option value={item.revision} key={item.revision}>
                    Revision {item.revision} · {item.title} ·{" "}
                    {item.effective_from || "No start date"} –{" "}
                    {item.effective_to || "No end date"}
                  </option>
                ))}
              </select>
            </label>
          )}
          <p>
            Revision {preview.revision} · Characters{" "}
            {preview.offset.toLocaleString()}–
            {(
              preview.offset + Array.from(preview.content).length
            ).toLocaleString()}{" "}
            of {preview.total_characters.toLocaleString()}. Preview shows saved
            text.
          </p>
          <pre className="document-preview">{preview.content}</pre>
          {workspace && (
            <div className="button-row">
              <button
                type="button"
                className="button secondary"
                disabled={busy || previousOffsets.length === 0}
                onClick={() =>
                  void loadPreview(
                    preview.revision,
                    previousOffsets[previousOffsets.length - 1],
                    "previous",
                  )
                }
              >
                Previous page
              </button>
              <button
                type="button"
                className="button secondary"
                disabled={busy || preview.next_offset === null}
                onClick={() =>
                  void loadPreview(
                    preview.revision,
                    preview.next_offset!,
                    "next",
                  )
                }
              >
                Next page
              </button>
            </div>
          )}
        </section>
      )}
      {blocker.state === "blocked" && (
        <div className="dialog-overlay">
          <div
            className="panel dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="document-leave-title"
          >
            <h2 id="document-leave-title">Leave without saving?</h2>
            <p>Your document changes have not been saved.</p>
            <div className="button-row">
              <button
                className="button primary"
                onClick={() => blocker.reset()}
              >
                Stay here
              </button>
              <button
                className="button secondary"
                onClick={() => {
                  close();
                  blocker.proceed();
                }}
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
