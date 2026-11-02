import { useEffect, useState } from "react";
import { useBlocker } from "react-router-dom";
import { request } from "./data";

type Summary = {
  id: string;
  title: string;
  filename: string;
  updated_at: string;
};
type Document = Summary & { content: string };
type Draft = { title: string; filename: string; content: string };
const example: Document = {
  id: "example",
  title: "Studio welcome",
  filename: "welcome.md",
  content: "# Welcome\n\nThis is an illustrative studio document.",
  updated_at: "2026-01-01T00:00:00Z",
};
const bytesToBase64 = (bytes: Uint8Array) => {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 8192)
    binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
  return btoa(binary);
};

export function DocumentsPage({
  workspace,
  csrf,
}: {
  workspace: boolean;
  csrf: string;
}) {
  const [documents, setDocuments] = useState<Summary[]>();
  const [saved, setSaved] = useState<Document>();
  const [draft, setDraft] = useState<Draft>();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const dirty =
    workspace &&
    !!draft &&
    (!saved ||
      draft.title !== saved.title ||
      draft.filename !== saved.filename ||
      draft.content !== saved.content);
  const blocker = useBlocker(dirty);
  useEffect(() => {
    let active = true;
    setError("");
    (workspace
      ? request<Summary[]>("/api/v1/documents")
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
  }, [workspace, attempt]);
  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (dirty) event.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);
  async function selectDocument(id: string) {
    if (dirty && !window.confirm("Discard unsaved changes?")) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const value = workspace
        ? await request<Document>(`/api/v1/documents/${id}`)
        : example;
      setSaved(value);
      setDraft(value);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function chooseFile(file?: File, newDocument = false) {
    if (!file || busy) return;
    setBusy(true);
    try {
      if (!/\.(txt|md)$/i.test(file.name))
        throw new Error("Choose a .txt or .md file.");
      if (file.size > 1_000_000)
        throw new Error("Documents must be at most 1 MB.");
      const content = new TextDecoder("utf-8", { fatal: true }).decode(
        await file.arrayBuffer(),
      );
      if (content.includes("\0"))
        throw new Error("The file must contain text.");
      if (newDocument) setSaved(undefined);
      setDraft((current) => ({
        title:
          (!newDocument && current?.title) ||
          file.name.replace(/\.(txt|md)$/i, ""),
        filename: file.name,
        content,
      }));
      setError("");
      setMessage("");
    } catch (err) {
      setError((err as Error).message || "The file must be valid UTF-8 text.");
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
      const value = await request<Document>(
        `/api/v1/documents${saved ? `/${saved.id}` : ""}`,
        {
          method: saved ? "PUT" : "POST",
          headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
          body: JSON.stringify({
            title: draft.title,
            filename: draft.filename,
            content_base64: bytesToBase64(
              new TextEncoder().encode(draft.content),
            ),
          }),
        },
      );
      setDocuments((current) => [
        value,
        ...(current || []).filter((item) => item.id !== value.id),
      ]);
      setSaved(value);
      setDraft(value);
      setMessage("Document saved.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function remove() {
    if (
      !saved ||
      busy ||
      !window.confirm(`Delete “${saved.title}”? This cannot be undone.`)
    )
      return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await request(`/api/v1/documents/${saved.id}`, {
        method: "DELETE",
        headers: { "X-CSRF-Token": csrf },
      });
      setDocuments((current) =>
        current?.filter((item) => item.id !== saved.id),
      );
      setSaved(undefined);
      setDraft(undefined);
      setMessage("Document deleted.");
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
                    {item.filename.toLowerCase().endsWith(".md")
                      ? "Markdown"
                      : "Text"}{" "}
                    · Updated {new Date(item.updated_at).toLocaleDateString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {workspace && (
            <label>
              Upload a document (.txt or .md, up to 1 MB)
              <input
                type="file"
                accept=".txt,.md,text/plain,text/markdown"
                disabled={busy}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (
                    file &&
                    dirty &&
                    !window.confirm("Discard unsaved changes?")
                  ) {
                    event.target.value = "";
                    return;
                  }
                  void chooseFile(file, true);
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
            <p>File: {draft.filename}</p>
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
          </fieldset>
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
                  if (!dirty || window.confirm("Discard unsaved changes?")) {
                    setDraft(undefined);
                    setSaved(undefined);
                  }
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
