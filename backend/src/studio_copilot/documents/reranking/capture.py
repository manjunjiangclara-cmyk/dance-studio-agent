"""Bounded immutable candidate snapshots; no neural inference in database transactions."""

from studio_copilot.documents.retrieval.engine import capture_candidates
from studio_copilot.documents.retrieval.experiment import require_api


def capture(engine, run_ids, query, as_of, tokenizer, *, allow_api=False, embedder=None):
    require_api(allow_api)
    result = capture_candidates(
        engine, run_ids, query, as_of, tokenizer, allow_api=allow_api, embedder=embedder
    )
    candidates = result.pop("results")
    routes = result.pop("candidates")
    return dict(result, candidates=candidates, candidate_routes=routes)
