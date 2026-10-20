from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class SlidingWindowLimiter:
    """Small in-process admission guard for the single-instance demo service."""

    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, now: float | None = None) -> bool:
        timestamp = monotonic() if now is None else now
        cutoff = timestamp - self.window_seconds
        with self._lock:
            requests = self._requests[key]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= limit:
                return False
            requests.append(timestamp)
            return True


create_run_limiter = SlidingWindowLimiter()
ai_explanation_limiter = SlidingWindowLimiter()
