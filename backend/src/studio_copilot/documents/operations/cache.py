"""Bounded in-process query vectors; no raw query storage or normalization."""

import hashlib
import time
from collections import OrderedDict
from concurrent.futures import Future
from threading import Lock


class QueryEmbeddingCache:
    def __init__(self, max_entries=128, ttl=300, clock=time.monotonic):
        if type(max_entries) is not int or max_entries < 1 or ttl <= 0:
            raise ValueError("Cache size and TTL must be positive.")
        self.max_entries, self.ttl, self.clock = max_entries, ttl, clock
        self.entries = OrderedDict()
        self.pending = {}
        self.lock = Lock()

    def get_or_compute(self, scope, profile, query, compute):
        from studio_copilot.documents.embedding.provider import validate_vector

        key = (scope, profile.key, hashlib.sha256(query.encode("utf-8")).digest())
        with self.lock:
            now = self.clock()
            for stale in [k for k, (until, _) in self.entries.items() if until <= now]:
                del self.entries[stale]
            if key in self.entries:
                self.entries.move_to_end(key)
                return list(self.entries[key][1]), True
            waiting = self.pending.get(key)
            owner = waiting is None
            if owner:
                waiting = self.pending[key] = Future()
        if not owner:
            return list(waiting.result()), True
        try:
            vector = validate_vector(compute())
            with self.lock:
                self.entries[key] = (self.clock() + self.ttl, tuple(vector))
                while len(self.entries) > self.max_entries:
                    self.entries.popitem(last=False)
            waiting.set_result(tuple(vector))
            return list(vector), False
        except BaseException as error:
            waiting.set_exception(error)
            raise
        finally:
            with self.lock:
                self.pending.pop(key, None)
