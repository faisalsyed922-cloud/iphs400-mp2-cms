"""Per-account login rate limit: too many recent failures locks the email out."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

MAX_FAILURES = 5
WINDOW_SECONDS = 15 * 60


class LoginLimiter:
    def __init__(self, clock: Callable[[], float] = time.time):
        self.clock = clock
        self._failures: dict[str, list[float]] = defaultdict(list)

    @staticmethod
    def _key(email: str) -> str:
        return email.strip().lower()

    def _recent(self, email: str) -> list[float]:
        cutoff = self.clock() - WINDOW_SECONDS
        recent = [t for t in self._failures[self._key(email)] if t > cutoff]
        self._failures[self._key(email)] = recent
        return recent

    def is_locked(self, email: str) -> bool:
        return len(self._recent(email)) >= MAX_FAILURES

    def record_failure(self, email: str) -> None:
        self._recent(email).append(self.clock())

    def reset(self) -> None:
        self._failures.clear()


login_limiter = LoginLimiter()
