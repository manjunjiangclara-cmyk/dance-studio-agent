"""Revision-pinned preparation and resumable, explicitly invoked embedding."""

from collections import Counter
from uuid import UUID

from sqlalchemy import Engine

from studio_copilot.documents.chunking import Chunker, Tokenizer, load_revision

from .provider import Embedder, EmbeddingError, EmbeddingProfile
from .store import Store


def plan(
    engine: Engine,
    document_id: UUID,
    revision: int,
    tokenizer: Tokenizer,
    profile: EmbeddingProfile,
):
    chunker = Chunker(load_revision(engine, document_id, revision), tokenizer)
    store = Store(engine, profile)
    counts = Counter()
    seen, pending = set(), {}
    new_tokens, cached_inputs = 0, 0
    for record in chunker.records():
        counts[record["kind"]] += 1
        if record["kind"] == "passage" and record["text_sha256"] not in seen:
            seen.add(record["text_sha256"])
            pending[record["text_sha256"]] = record["token_count"]
        if len(pending) >= 64:
            cached = store.cached_hashes(pending)
            cached_inputs += len(cached)
            new_tokens += sum(count for key, count in pending.items() if key not in cached)
            pending.clear()
    cached = store.cached_hashes(pending)
    cached_inputs += len(cached)
    new_tokens += sum(count for key, count in pending.items() if key not in cached)
    return dict(
        document_id=str(document_id),
        revision=revision,
        parents=counts["parent"],
        passages=counts["passage"],
        unique_inputs=len(seen),
        cached_inputs=cached_inputs,
        estimated_new_tokens=new_tokens,
        warnings=sorted(chunker.warnings),
        profile_hash=profile.key,
        chunker_hash=chunker.config_hash,
        dry_run=True,
    )


def run(
    engine: Engine,
    document_id: UUID,
    revision: int,
    tokenizer: Tokenizer,
    profile: EmbeddingProfile,
    *,
    embedder=None,
    progress=lambda value: None,
):
    chunker = Chunker(load_revision(engine, document_id, revision), tokenizer)
    store = Store(engine, profile)
    run_id, token = store.claim(chunker)
    if token is None:
        return store.status(run_id)
    try:
        status = store.status(run_id)
        progress(status)
        if not status["prepared"]:
            batch, passages, total = [], 0, 0
            for ordinal, record in enumerate(chunker.records()):
                batch.append((ordinal, record))
                total += 1
                passages += record["kind"] == "passage"
                if len(batch) == 64:
                    store.save_chunks(run_id, token, batch)
                    batch.clear()
            if batch:
                store.save_chunks(run_id, token, batch)
            store.prepared(run_id, token, total, passages)
        while (texts := store.missing(run_id, token)) is not None:
            if not texts:
                continue
            for value in texts:
                if tokenizer.count(value) > 900 or not value.strip():
                    raise EmbeddingError(
                        "invalid_chunks", "Stored passage violates its token budget."
                    )
            if embedder is None:
                # No API key/client is needed when all vectors are already cached.
                embedder = Embedder(profile)
            vectors, usage = embedder.embed(
                texts, before_attempt=lambda: store.heartbeat(run_id, token, attempt=True)
            )
            store.save_vectors(run_id, token, texts, vectors, usage)
            progress(store.status(run_id))
        store.complete(run_id, token)
        return store.status(run_id)
    except BaseException as error:
        code = error.code if isinstance(error, EmbeddingError) else "processing_failed"
        try:
            store.fail(run_id, token, code)
        except Exception:
            # A disconnected DB cannot record failure; the lease still expires safely.
            pass
        raise
