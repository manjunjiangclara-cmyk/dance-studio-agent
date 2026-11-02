# Document ingestion

Documents remain outside the agent's knowledge base. Ingestion validates and retains source material; it does not publish, index, retrieve, or make model calls.

## Owner workflow

Upload one UTF-8 `.md` or `.txt` file of at most 10,000,000 bytes. Set its title and optional effective-from/to dates, then save. Files of at most 1,000,000 bytes can be edited inline; larger files use a paginated preview and file replacement. The saved-revision selector previews historical text without changing the current document or local edits.

Every changed save creates an immutable revision, including metadata-only edits. Byte-identical content with identical metadata on the same document is a no-op. Different documents remain independent; matching current content hashes produce a duplicate notice (up to 20 matches). Concurrent edits return a conflict; local edits remain available until the owner explicitly discards them and reloads.

Original uploaded bytes are preserved as UTF-8 text without newline, BOM, or Unicode normalization. The revision SHA-256 is calculated while receiving the file. `hash_origin=upload_bytes` identifies multipart uploads; `stored_text_utf8` identifies hashes reconstructed from existing stored text, the legacy base64 API, or inline editing. A reconstructed hash does not claim original-upload provenance.

Existing empty/whitespace-only documents survive migration with `ingestion_status=needs_correction`; replace or edit them to supply valid text. New blank content, NUL, invalid UTF-8, path-like filenames, and reversed date ranges are rejected. Dates are entered by the owner and not inferred from prose. Deleting a document also deletes its revisions.

## API

All paths below are relative to `/api/v1/documents`. Owner browser writes require the configured origin and CSRF token. The existing admin bearer credential remains supported. No anonymous document access is added.

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/upload` | Multipart `file`, `title`, optional ISO `effective_from`/`effective_to`; returns metadata with status 201 |
| PUT | `/{id}/upload` | Same fields plus required `expected_revision`; replaces a file |
| GET | `/{id}/metadata` | Current metadata and duplicate notices, without text |
| PATCH | `/{id}/metadata` | `title`, required `expected_revision`, optional effective dates; omitted dates are preserved, explicit null clears them |
| PUT | `/{id}/text` | `title`, `filename`, `content`, `expected_revision`, optional effective dates; small-file editor |
| GET | `/{id}/revisions` | Revision metadata, newest first, without source text |
| GET | `/{id}/revisions/{revision}/preview` | `offset` (Unicode characters, default 0), `limit` (1–20,000); returns bounded text and `next_offset` or null |

Preview pages prefer line boundaries where possible; long individual lines remain bounded. A preview's revision never changes during pagination. Source text is displayed as text, not executed HTML.

Existing list and base64 create/read/update/delete endpoints remain. Base64 content stays limited to 1,000,000 bytes, and updates must supply `expected_revision` (missing/stale values return 409). Legacy detail reads for larger documents return `409 document_preview_required`; use metadata and revision previews. Inline editing a current large document also returns that error; use file replacement.

Multipart requests are authenticated before reading. Actual incoming request bytes are limited to 10,065,536, and file bytes independently to 10,000,000. Metadata fields, headers, part count, and parsing batches are bounded. The parser writes to one automatically closed temporary file; database write transactions begin after validation. `Content-Length` is checked when present but never replaces actual-byte accounting. Successful ingestion materializes at most one bounded source file in memory before storing it in PostgreSQL.

The migration adds `documents.current_revision` and `document_revisions`; PostgreSQL rejects updates to stored revision rows. Apply it using the normal `alembic upgrade head` workflow. No new worker, vector extension, external storage, or API key is required.
