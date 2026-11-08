# Offline local reranking

Reranking is implemented as a measured, optional offline experiment. **Normal keyword/vector/hybrid search, the app UI, and the agent do not use it.** No schema migration, publication, generation, confidence threshold, or abstention is added. The local models score question–passage pairs; they do not create replacement embeddings or determine authoritative policy.

## Workflow

From `backend/`, use native Python 3.12. Current macOS PyTorch wheels require Apple Silicon; an Intel/Rosetta Python on an ARM Mac cannot install them. The existing backend installation does not require neural dependencies. `rerank` is an optional locked dependency group.

```bash
# Use a native interpreter when creating the optional reranking environment.
uv sync --locked --group rerank --python /path/to/native/python3.12

# Public model download only; no OpenAI inference. Explicit network opt-in.
uv run --group rerank python -m studio_copilot.documents.reranking prepare-models \
  --model-cache /tmp/studio-rerank-models --allow-download

# Local-only dataset/token estimate. Requires the explicitly prepared chunk tokenizer.
uv run python -m studio_copilot.documents.reranking plan \
  --tokenizer-cache /tmp/studio-chunking-tokenizer

# Paid real document/question embeddings and candidate capture.
# TEST_DATABASE_URL must name a dedicated PostgreSQL database ending _test.
uv run --env-file .env python -m studio_copilot.documents.reranking capture \
  --output-dir evaluations/results/my-reranking-capture --allow-api \
  --tokenizer-cache /tmp/studio-chunking-tokenizer

# Offline local neural inference; no OpenAI calls or DB access.
uv run --group rerank python -m studio_copilot.documents.reranking compare \
  --capture-dir evaluations/results/my-reranking-capture \
  --model-cache /tmp/studio-rerank-models \
  --output-dir evaluations/results/my-reranking-comparison \
  --tokenizer-cache /tmp/studio-chunking-tokenizer
```

Existing output directories are refused. Failed captures retain a completion/cleanup/usage manifest and cannot be compared. Candidate snapshots contain fictional source text; model weights, virtual environments, and raw capture outputs are not committed.

Preparation downloads only allowlisted tokenizer/configuration files and safetensors weights for `cross-encoder/ms-marco-MiniLM-L6-v2` and `cross-encoder/ms-marco-MiniLM-L12-v2`. It resolves immutable model commit IDs and hashes every asset. Reuse verifies cache contents; missing, altered, unexpected or symlinked files are rejected. Normal inference requires local files, disables remote model code, and never downloads weights. Scores remain raw logits, not probabilities of correctness.

## Retrieval and inference contracts

Capture shares the normal retrieval pipeline: validate explicit immutable runs/date, embed the question outside database transactions, then use one read-only repeatable-read snapshot for both routes, references and parent records. Each route contributes at most 20 distinct texts; the deduplicated union contains at most 40. Capture materializes all candidates and their representative parents before closing the snapshot. Normal search continues to materialize and return only its original six results.

Every comparison replays exactly the same checksummed candidate records. Cross-encoding happens after capture, without a database connection. It may reorder eligible passages but cannot modify their source references. The final six use the same parent-expansion rules and 12,000 `cl100k_base` token budget as normal search. Expanded coverage counts only actually packed evidence; visible alternative references can count for passage-source coverage without pretending their parent text was packed.

Inference uses PyTorch CPU float32, four threads, evaluation mode, disabled gradients, and batches of at most 16 windows across candidates. Model-token limits are separate from the chunk tokenizer: question maximum 256 tokens; complete pair maximum 512 including special tokens. Passage token IDs are windowed with 64-token overlap and the full question repeated in each pair. Maximum window score determines passage rank. No passage tail is silently dropped. Ties preserve original RRF rank, then text hash. Oversized questions, invalid scores and model failures are explicit failed cases, with no baseline fallback labelled as successful reranking.

## Frozen data and selection

The experiment combines the unchanged 16-document/100-question retrieval corpus with eight independently authored sources and 50 fresh questions. All paths search the same 24 documents / 279 distinct passage texts. The existing tuning split remains tuning; the already inspected held-out split is renamed **diagnostic**. Fresh questions cover guest teachers, instrument loans, overnight tours and sensory support: 40 answerable, eight in-period unanswered, two date-excluded. Sixteen fresh cases require multiple documents; four concern active conflicts; two place required evidence beyond the first model window.

Sources, exact original Unicode evidence ranges, answerability, dates and manifest hashes were independently audited and frozen before model runs. Each model first runs on development data only. Selection uses tuning complete-evidence coverage, recall, MRR, lower warm p95, then L6 as the final tie preference. Diagnostic scores do not affect selection. `selection.json` records the model/revision, dataset/capture hashes, development report hashes, rule and gates **before** any fresh validation scoring. A fresh worker rejects a different selection, model, revision, dataset or capture. Only the selected model is tested on fresh validation.

Adoption gates are predeclared: at least 2.5 percentage points of fresh complete-evidence improvement; no Recall@6 reduction; at most 0.01 MRR reduction; no multi-source complete-evidence reduction; no failed cases or source/date violations; warm CPU reranking p95 at most two seconds. These are practical experiment gates, not statistical significance tests. Passing them produces a recommendation, not automatic activation in normal search.

## Actual measurement — 2026-11-08

Both local models ran with real weights. All source/query vectors came from real OpenAI `text-embedding-3-small`, 1,536 dimensions, in a fresh owned schema that was removed after capture. The main document library was unchanged. Preparation used 24 requests / 38,239 reported input tokens; capture used 144 question requests / 2,282 tokens. **Total: 168 requests / 40,521 input tokens, no retries.** Local reranking added no provider calls.

| Tuning result: 40 answerable questions | Recall@6 | Complete evidence | MRR@6 | Warm p95 |
| --- | ---: | ---: | ---: | ---: |
| Original hybrid/RRF | 97.92% | 95% | 0.9583 | — |
| MiniLM-L6-v2 | 97.50% | 95% | 0.9500 | 424 ms |
| MiniLM-L12-v2 | 96.25% | 92.5% | 0.9750 | 817 ms |

The fixed tuning rule selected **L6**. Tuning does not show a recall improvement; the following independent-family validation is the adoption test.

| Fresh validation: 40 answerable questions | Recall@20 candidates | Recall@6 | Complete evidence | MRR@6 | Multi-source complete evidence |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original hybrid/RRF | 100% | 93.75% | 90% (36/40) | 0.9050 | 81.25% (13/16) |
| Selected MiniLM-L6-v2 | 100% | 97.50% | 95% (38/40) | 1.0000 | 87.50% (14/16) |

Fresh CPU reranking p50 was 194 ms and p95 was 331 ms; peak worker RSS was 876 MiB. Model loading plus warmup took 1.90 seconds in that worker and is excluded from per-question timing. Development process peaks were 855 MiB (L6) and 952 MiB (L12). A final verification replay with the identical frozen selection and candidates reproduced every fresh ranking and quality metric. It measured cold model loading at 2.28 seconds, warmup at 16 ms, warm p95 at 326 ms and peak RSS at 902 MiB; no model choice or settings changed. These are local measurements, not production SLAs or GPU benchmarks. Dependency versions, revisions, runtime parameters, per-case timings and window counts are in the report.

Both long-tail cases were fully recovered with two model windows. No fresh question lost evidence relative to baseline. The two remaining incomplete cases, `rv-018` and `rv-020`, both lose the ordinary 21-day instrument-loan period from final selection; parent expansion does not recover it. All fresh date exclusions passed. The selected model still returns candidates for all eight in-period unanswered questions; reranking does not establish answerability.

**The selected L6 model passes the declared fresh adoption gates.** It remains offline and normal search remains unchanged. Fixtures are hand-authored English challenge data, not production traffic. Some questions share scenarios, including the two remaining misses; 40 questions are correlated diagnostics, not independent statistical proof. The old diagnostic split is not a new holdout. The two models were not fine-tuned, no score thresholds were fitted, and no settings were changed after fresh results.

[Full measured comparison](measurements/reranking-live-2026-11-08.json), [frozen selection](measurements/reranking-live-2026-11-08-selection.json), and [real-embedding capture/cleanup manifest](measurements/reranking-live-2026-11-08-capture.json) retain the evidence. The [final verification report](measurements/reranking-live-2026-11-08-verification.json) records separate cold/warmup timing and runtime environment. Raw candidate snapshots stay in the ignored results directory and can be replayed without the removed database schema.

See the [consolidated test/evaluation summary](16-testing-and-evaluations.md) for automated coverage and the distinction between fake-provider tests, performance benchmarks and real model evaluation.
