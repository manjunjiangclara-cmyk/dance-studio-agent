"""Fixed fictional cache workload. No database, network, tokenizer, or model inference."""

import argparse
import json
import resource
import sys
import time

from studio_copilot.documents.embedding.provider import EmbeddingProfile
from studio_copilot.documents.operations import QueryEmbeddingCache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-delay-ms", type=float, default=1)
    args = parser.parse_args()
    if not 0 <= args.provider_delay_ms <= 100:
        parser.error("Use a simulated delay between 0 and 100 ms.")
    queries = [f"Fictional policy question {i}: when is notice required?" for i in range(100)]
    vector = [1.0] + [0.0] * 1535
    profile = EmbeddingProfile()
    calls = 0

    def compute():
        nonlocal calls
        calls += 1
        time.sleep(args.provider_delay_ms / 1000)
        return vector

    cache = QueryEmbeddingCache()
    phases = []
    for phase in ("cold", "warm", "warm_repeat"):
        before, started, hits = calls, time.perf_counter(), 0
        for query in queries:
            _, hit = cache.get_or_compute("fictional-benchmark", profile, query, compute)
            hits += hit
        phases.append(
            dict(
                phase=phase,
                queries=len(queries),
                cache_hits=hits,
                fake_provider_calls=calls - before,
                seconds=time.perf_counter() - started,
            )
        )
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(
        json.dumps(
            dict(
                version="operations-benchmark-v1",
                workload="100 distinct queries, 3 passes",
                simulated_provider_delay_ms=args.provider_delay_ms,
                phases=phases,
                total_fake_provider_calls=calls,
                uncached_call_baseline=300,
                calls_saved=300 - calls,
                peak_process_rss_bytes=rss if sys.platform == "darwin" else rss * 1024,
                model_calls=0,
                database_calls=0,
                note="Synthetic mechanism measurement, not provider latency or semantic quality.",
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
