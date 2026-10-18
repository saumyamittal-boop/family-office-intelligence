"""A small in-memory throttle for repeated wrong passwords or access codes.

Per process, so it resets when the server restarts. That is enough for a demo link: it stops quick
guessing without a database. It can also lock a real user out for a few minutes if someone hammers their
username, which is an accepted trade-off for a prototype.
"""
from __future__ import annotations

import math
import time


class Throttle:
    def __init__(self, max_failures: int = 5, window_seconds: float = 600.0, clock=time.monotonic):
        self.max_failures = max_failures
        self.window = window_seconds
        self._clock = clock
        self._failures: dict[str, list[float]] = {}

    def _recent(self, key: str) -> list[float]:
        cutoff = self._clock() - self.window
        recent = [t for t in self._failures.get(key, []) if t > cutoff]
        self._failures[key] = recent
        return recent

    def blocked_for(self, key: str) -> float:
        """Seconds until another attempt is allowed (0 if allowed now)."""
        recent = self._recent(key)
        if len(recent) < self.max_failures:
            return 0.0
        return max(0.0, recent[0] + self.window - self._clock())

    def record_failure(self, key: str) -> None:
        self._recent(key).append(self._clock())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)


def minutes(seconds: float) -> int:
    return max(1, math.ceil(seconds / 60))
