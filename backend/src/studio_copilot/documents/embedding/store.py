"""Short PostgreSQL transactions and database-clock lease fencing."""

import uuid
from dataclasses import asdict

from sqlalchemy import Engine, and_, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from studio_copilot.persistence.models import DocumentChunk as Chunk
from studio_copilot.persistence.models import EmbeddingRun as Run
from studio_copilot.persistence.models import EmbeddingVector as Vector

from .provider import EmbeddingError, EmbeddingProfile, sha256, validate_vector

LEASE = text("clock_timestamp() + interval '300 seconds'")


class LeaseLost(EmbeddingError):
    def __init__(self):
        super().__init__("lease_lost", "The run was deleted or this execution no longer owns it.")


class Store:
    def __init__(self, engine: Engine, profile: EmbeddingProfile):
        self.engine, self.profile = engine, profile

    def _owned(self, session, run_id, token):
        run = session.scalar(
            select(Run)
            .where(
                Run.id == run_id,
                Run.lease_token == token,
                Run.profile_hash == self.profile.key,
                Run.lease_expires_at > func.clock_timestamp(),
                Run.status.in_(["preparing", "running"]),
            )
            .with_for_update()
        )
        if run is None:
            raise LeaseLost()
        return run

    def _renew(self, session, run):
        # Recheck immediately before the short transaction completes, not just on entry.
        result = session.execute(
            update(Run)
            .where(
                Run.id == run.id,
                Run.lease_token == run.lease_token,
                Run.lease_expires_at > func.clock_timestamp(),
            )
            .values(lease_expires_at=LEASE)
        )
        if result.rowcount != 1:
            raise LeaseLost()

    def claim(self, chunker):
        source = chunker.source
        try:
            with Session(self.engine) as session, session.begin():
                session.execute(
                    insert(Run)
                    .values(
                        id=uuid.uuid4(),
                        document_id=uuid.UUID(source.document_id),
                        revision=source.revision,
                        chunker_hash=chunker.config_hash,
                        profile_hash=self.profile.key,
                        profile=asdict(self.profile),
                        source=source.metadata(),
                        chunker_config=asdict(chunker.config),
                        headings=chunker.headings,
                        warnings=sorted(chunker.warnings),
                        status="preparing",
                        prepared=False,
                    )
                    .on_conflict_do_nothing(
                        index_elements=["document_id", "revision", "chunker_hash", "profile_hash"]
                    )
                )
                run = session.scalar(
                    select(Run)
                    .where(
                        Run.document_id == uuid.UUID(source.document_id),
                        Run.revision == source.revision,
                        Run.chunker_hash == chunker.config_hash,
                        Run.profile_hash == self.profile.key,
                    )
                    .with_for_update()
                )
                if run is None:
                    raise LeaseLost()
                if run.status == "complete":
                    return run.id, None
                busy = session.scalar(
                    select(
                        and_(
                            Run.lease_token.is_not(None),
                            Run.lease_expires_at > func.clock_timestamp(),
                        )
                    ).where(Run.id == run.id)
                )
                if busy:
                    raise EmbeddingError(
                        "busy", "This preparation run already has an active owner."
                    )
                token = uuid.uuid4()
                run.lease_token, run.lease_expires_at = token, LEASE
                run.status = "running" if run.prepared else "preparing"
                run.error_code = None
                return run.id, token
        except IntegrityError:
            raise EmbeddingError("source_missing", "The selected revision was deleted.") from None

    def heartbeat(self, run_id, token, *, attempt=False):
        with Session(self.engine) as session, session.begin():
            run = self._owned(session, run_id, token)
            if attempt:
                run.attempts += 1
            session.flush()
            self._renew(session, run)

    def save_chunks(self, run_id, token, records):
        with Session(self.engine) as session, session.begin():
            run = self._owned(session, run_id, token)
            if run.prepared:
                raise EmbeddingError("invalid_state", "Prepared chunk text is immutable.")
            values = []
            for ordinal, record in records:
                if sha256(record["text"]) != record["text_sha256"]:
                    raise EmbeddingError("invalid_chunks", "Chunk text/hash mismatch.")
                values.append(
                    dict(
                        run_id=run_id,
                        chunk_id=record["id"],
                        profile_hash=self.profile.key,
                        ordinal=ordinal,
                        kind=record["kind"],
                        parent_id=record["parent_id"],
                        text=record["text"],
                        text_sha256=record["text_sha256"],
                        token_count=record["token_count"],
                        provenance={
                            k: v
                            for k, v in record.items()
                            if k
                            not in {"id", "kind", "parent_id", "text", "text_sha256", "token_count"}
                        },
                    )
                )
            if values:
                session.execute(insert(Chunk).values(values).on_conflict_do_nothing())
                saved = session.execute(
                    select(
                        Chunk.chunk_id,
                        Chunk.ordinal,
                        Chunk.text,
                        Chunk.text_sha256,
                        Chunk.provenance,
                        Chunk.kind,
                        Chunk.parent_id,
                        Chunk.token_count,
                        Chunk.profile_hash,
                    ).where(
                        Chunk.run_id == run_id, Chunk.chunk_id.in_([v["chunk_id"] for v in values])
                    )
                )
                indexed = {row.chunk_id: row._mapping for row in saved}
                for value in values:
                    actual = indexed.get(value["chunk_id"])
                    if actual is None or any(actual[key] != value[key] for key in actual):
                        raise EmbeddingError(
                            "invalid_chunks", "Existing chunks differ from source."
                        )
            self._renew(session, run)

    def prepared(self, run_id, token, total, passages):
        with Session(self.engine) as session, session.begin():
            run = self._owned(session, run_id, token)
            count, passage_count = session.execute(
                select(func.count(), func.count().filter(Chunk.kind == "passage")).where(
                    Chunk.run_id == run_id
                )
            ).one()
            if count != total or passage_count != passages:
                raise EmbeddingError("incomplete", "Prepared chunk count mismatch.")
            run.prepared, run.expected_chunks, run.expected_passages = True, total, passages
            run.status = "running"
            session.flush()
            self._renew(session, run)

    def missing(self, run_id, token):
        """Attach cache hits and return at most 64 unique uncached inputs, detached."""
        with Session(self.engine) as session, session.begin():
            run = self._owned(session, run_id, token)
            if not run.prepared:
                raise EmbeddingError("invalid_state", "Finish preparing chunks before embedding.")
            rows = session.execute(
                select(Chunk.text_sha256, Chunk.text)
                .where(Chunk.run_id == run_id, Chunk.kind == "passage", Chunk.vector_key.is_(None))
                .order_by(Chunk.ordinal)
                .limit(64)
            ).all()
            inputs = dict(rows)
            for input_sha, value in inputs.items():
                if sha256(value) != input_sha:
                    raise EmbeddingError("invalid_chunks", "Stored chunk text/hash mismatch.")
            cached = session.execute(
                select(Vector.input_sha256, Vector.key).where(
                    Vector.profile_hash == self.profile.key, Vector.input_sha256.in_(inputs)
                )
            ).all()
            for input_sha, key in cached:
                session.execute(
                    update(Chunk)
                    .where(
                        Chunk.run_id == run_id,
                        Chunk.kind == "passage",
                        Chunk.text_sha256 == input_sha,
                    )
                    .values(vector_key=key)
                )
                inputs.pop(input_sha)
            self._renew(session, run)
            # None means no pending chunks; [] means this batch was entirely cached.
            return list(inputs.values()) if rows else None

    def save_vectors(self, run_id, token, texts, vectors, usage):
        if (
            len(texts) != len(vectors)
            or not texts
            or len(texts) > 64
            or type(usage) is not int
            or usage < 0
        ):
            raise EmbeddingError("invalid_vectors", "Invalid embedding checkpoint.")
        vectors = [validate_vector(vector) for vector in vectors]
        hashes = [sha256(value) for value in texts]
        if len(set(hashes)) != len(hashes):
            raise EmbeddingError("invalid_vectors", "Embedding inputs must be deduplicated.")
        with Session(self.engine) as session, session.begin():
            # Ownership/deletion is checked BEFORE any shared-cache insert.
            run = self._owned(session, run_id, token)
            expected = set(
                session.scalars(
                    select(Chunk.text_sha256).where(
                        Chunk.run_id == run_id,
                        Chunk.kind == "passage",
                        Chunk.text_sha256.in_(hashes),
                    )
                )
            )
            if expected != set(hashes):
                raise EmbeddingError(
                    "invalid_chunks", "Embedding inputs do not belong to this run."
                )
            session.execute(
                insert(Vector)
                .values(
                    [
                        dict(
                            key=self.profile.vector_key(value),
                            profile_hash=self.profile.key,
                            input_sha256=value,
                            embedding=vector,
                        )
                        for value, vector in zip(hashes, vectors)
                    ]
                )
                .on_conflict_do_nothing()
            )
            for value in hashes:
                session.execute(
                    update(Chunk)
                    .where(
                        Chunk.run_id == run_id, Chunk.kind == "passage", Chunk.text_sha256 == value
                    )
                    .values(vector_key=self.profile.vector_key(value))
                )
            run.reported_tokens += usage
            session.flush()
            self._renew(session, run)

    def complete(self, run_id, token):
        with Session(self.engine) as session, session.begin():
            run = self._owned(session, run_id, token)
            total, passages, pending = session.execute(
                select(
                    func.count(),
                    func.count().filter(Chunk.kind == "passage"),
                    func.count().filter(and_(Chunk.kind == "passage", Chunk.vector_key.is_(None))),
                ).where(Chunk.run_id == run_id)
            ).one()
            if (
                not run.prepared
                or total != run.expected_chunks
                or passages != run.expected_passages
                or pending
            ):
                raise EmbeddingError("incomplete", "Not every expected passage has a valid vector.")
            self._renew(session, run)
            run.status, run.lease_token, run.lease_expires_at = "complete", None, None

    def fail(self, run_id, token, code):
        try:
            with Session(self.engine) as session, session.begin():
                run = self._owned(session, run_id, token)
                run.status, run.error_code = "failed", code
                run.lease_token, run.lease_expires_at = None, None
        except LeaseLost:
            pass

    def status(self, run_id):
        with Session(self.engine) as session:
            # A single statement pins metadata/counts to the same MVCC snapshot and
            # avoids loading the full heading registry merely to show progress.
            row = (
                session.execute(
                    select(
                        Run.id.label("run_id"),
                        Run.document_id,
                        Run.revision,
                        Run.status,
                        Run.prepared,
                        func.coalesce(Run.lease_expires_at > func.clock_timestamp(), False).label(
                            "lease_active"
                        ),
                        func.count(Chunk.chunk_id).label("chunks"),
                        func.count(Chunk.chunk_id)
                        .filter(Chunk.kind == "passage")
                        .label("passages"),
                        func.count(Chunk.chunk_id)
                        .filter(and_(Chunk.kind == "passage", Chunk.vector_key.is_not(None)))
                        .label("embedded_passages"),
                        Run.expected_passages,
                        Run.reported_tokens,
                        Run.attempts,
                        Run.error_code,
                        Run.warnings,
                        Run.profile,
                        Run.chunker_hash,
                    )
                    .outerjoin(Chunk, Chunk.run_id == Run.id)
                    .where(Run.id == run_id)
                    .group_by(Run.id)
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise EmbeddingError("not_found", "The preparation run does not exist.")
            result = dict(row)
            result["run_id"], result["document_id"] = str(row["run_id"]), str(row["document_id"])
            return result

    def cached_hashes(self, hashes):
        # Used by dry-run only; never constructs a provider or writes to PostgreSQL.
        if not hashes:
            return set()
        with Session(self.engine) as session:
            return set(
                session.scalars(
                    select(Vector.input_sha256).where(
                        Vector.profile_hash == self.profile.key, Vector.input_sha256.in_(hashes)
                    )
                )
            )
