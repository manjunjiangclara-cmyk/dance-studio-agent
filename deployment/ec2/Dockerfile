FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.11.8 AS uv
FROM python:3.12-slim-bookworm
COPY --from=uv /uv /uvx /bin/
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never \
    PATH=/app/backend/.venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    WEBSITE_DIST=/app/frontend/dist STUDIO_TOKENIZER_CACHE=/app/assets/tokenizer \
    STUDIO_RERANKER_CACHE=/app/assets/reranker \
    STUDIO_POLICY_PATH=/data/policy/studio.yaml STUDIO_PUBLIC_DEMO_DB=/data/public-demo/ledger.sqlite3 \
    OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false CUDA_VISIBLE_DEVICES=""
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --group rerank --no-install-project
COPY backend/src/ ./src/
COPY backend/migrations/ ./migrations/
COPY backend/alembic.ini ./
COPY backend/policies/ /app/default-policy/
RUN uv sync --frozen --no-dev --group rerank \
    && python -m studio_copilot.documents.chunking --prepare-tokenizer --tokenizer-cache /app/assets/tokenizer \
    && python -c 'from studio_copilot.documents.reranking.runtime import prepare_models; prepare_models("/app/assets/reranker", allow_download=True)' \
    && python -c 'from studio_copilot.documents.reranking.runtime import LocalReranker; r=LocalReranker("/app/assets/reranker", "cross-encoder/ms-marco-MiniLM-L6-v2"); assert len(r.rank("ballet", [{"text":"A ballet class", "text_sha256":"build-smoke"}])) == 1' \
    && useradd --uid 10001 --create-home studio
COPY --from=frontend /build/dist/ /app/frontend/dist/
# Tokenizer preparation uses a mode-0600 temporary file; it is a public vocabulary.
RUN chmod 644 /app/assets/tokenizer/cl100k_base.tiktoken
USER 10001:10001
RUN python -c 'from pathlib import Path; from studio_copilot.documents.chunking import Tokenizer; from studio_copilot.documents.reranking.runtime import LocalReranker; Tokenizer(Path("/app/assets/tokenizer")); r=LocalReranker("/app/assets/reranker", "cross-encoder/ms-marco-MiniLM-L6-v2"); assert len(r.rank("ballet", [{"text":"A ballet class", "text_sha256":"nonroot-smoke"}])) == 1'
EXPOSE 8000
CMD ["uvicorn", "studio_copilot.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*", "--no-access-log"]
