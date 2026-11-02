import { useEffect, useState } from "react";
import { useBlocker } from "react-router-dom";
import { ApiError, request } from "./data";
import "./documents.css";

type Summary = {
  id: string;
  title: string;
  filename: string;
  updated_at: string;
  current_revision: number;
  byte_size: number;
  sha256: string;
  hash_origin: string;
  ingestion_status: string;
  effective_from: string | null;
  effective_to: string | null;
  duplicates?: { id: string; title: string }[];
};
type Revision = Summary & { revision: number; created_at: string };
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
  const dirty =
    workspace &&
    !!draft &&
    (!!file || JSON.stringify(draft) !== JSON.stringify(original));
  const blocker = useBlocker(dirty);

  useEffect(() => {
    let active = true;
    (workspace ? request<Summary[]>(root) : Promise.resolve([example]))
      .then((value) => {
        if (active) setDocuments(value);
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

  function fail(err: unknown) {
    setError((err as Error).message);
    setConflict(err instanceof ApiError && err.status === 409);
  }
  async function loadDocument(id: string) {
    const value = workspace
      ? await request<Summary>(`${root}/${id}/metadata`)
      : example;
    const [history, content] = await Promise.all([
      workspace
        ? request<Revision[]>(`${root}/${id}/revisions`)
        : Promise.resolve([]),
      value.byte_size <= 1_000_000
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
    const first = workspace
      ? await request<Preview>(
          `${root}/${id}/revisions/${value.current_revision}/preview`,
        )
      : {
          revision: 1,
          content: example.content,
          offset: 0,
          next_offset: null,
          total_characters: example.content.length,
        };
    const next = makeDraft(value, content?.content);
    setSaved(value);
    setOriginal(next);
    setDraft(next);
    setFile(undefined);
    setFileText(undefined);
    setRevisions(history);
    setPreview(first);
    setPreviousOffsets([]);
    setConflict(false);
  }
  async function selectDocument(id: string) {
    if (
      dirty &&
      !window.confirm("Discard unsaved changes and load the current version?")
    )
      return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await loadDocument(id);
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
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
    if (!workspace || !draft || busy) return;
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
      setMessage("Document saved. Not published or used by the agent.");
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
  async function remove() {
    if (
      !saved ||
      busy ||
      !window.confirm(
        `Delete “${saved.title}” and all its revisions? This cannot be undone.`,
      )
    )
      return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await request(`${root}/${saved.id}`, {
        method: "DELETE",
        headers: { "X-CSRF-Token": csrf },
      });
      setDocuments((current) =>
        current?.filter((item) => item.id !== saved.id),
      );
      close();
      setMessage("Document deleted.");
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
    setBusy(true);
    setError("");
    try {
      const value = await request<Preview>(
        `${root}/${saved.id}/revisions/${revision}/preview?offset=${offset}`,
      );
      setPreviousOffsets((current) =>
        direction === "next"
          ? [...current, preview?.offset || 0]
          : direction === "previous"
            ? current.slice(0, -1)
            : [],
      );
      setPreview(value);
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <h2>Documents</h2>
          <p>
            Manage studio reference material. Documents are not yet used by the
            agent.
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
          {documents.length === 0 ? (
            <p>
              No documents yet. Upload a text or Markdown file to get started.
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
          {workspace && (
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
              . Not published.
            </p>
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
          <fieldset disabled={!workspace || busy}>
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
          {workspace && (
            <div className="button-row">
              <button
                className="button primary"
                disabled={!dirty || busy || !draft.title.trim()}
              >
                {busy ? "Working…" : "Save document"}
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
                  disabled={busy}
                  onClick={() => void remove()}
                >
                  Delete document
                </button>
              )}
              {dirty && <span>Unsaved changes</span>}
            </div>
          )}
        </form>
      )}
      {saved && preview && (
        <section className="panel policy-form" aria-label="Revision preview">
          <h2>Saved revision preview</h2>
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
