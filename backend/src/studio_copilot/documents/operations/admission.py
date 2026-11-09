"""Single-process studio upload admission, after auth and before body reads."""

import math
import time
from collections import deque
from threading import Lock

from fastapi import HTTPException


class UploadLimiter:
    def __init__(self, limit=30, window=60, clock=time.monotonic):
        if type(limit) is not int or limit < 1 or window <= 0:
            raise ValueError("Upload admission limits must be positive.")
        self.limit, self.window, self.clock = limit, window, clock
        self.timestamps = deque()
        self.lock = Lock()

    def check(self):
        with self.lock:
            now = self.clock()
            while self.timestamps and self.timestamps[0] <= now - self.window:
                self.timestamps.popleft()
            if len(self.timestamps) >= self.limit:
                retry = max(1, math.ceil(self.timestamps[0] + self.window - now))
                raise HTTPException(
                    429, "Document upload rate limit exceeded.", headers={"Retry-After": str(retry)}
                )
            self.timestamps.append(now)
