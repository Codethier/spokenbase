# SPDX-License-Identifier: AGPL-3.0-only

"""Thread-safe health state shared by FastAPI and the Redpanda consumer."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    uptime_seconds: float
    queue_enabled: bool
    queue_connected: bool
    messages_handled: int
    active_jobs: int
    last_error_code: str | None

    @property
    def ready(self) -> bool:
        return not self.queue_enabled or self.queue_connected


class RuntimeState:
    def __init__(self, *, queue_enabled: bool) -> None:
        self._started_at = time.monotonic()
        self._queue_enabled = queue_enabled
        self._queue_connected = False
        self._messages_handled = 0
        self._active_jobs = 0
        self._last_error_code: str | None = None
        self._lock = Lock()

    def mark_queue_connected(self) -> None:
        with self._lock:
            self._queue_connected = True
            self._last_error_code = None

    def mark_queue_disconnected(self, error_code: str | None = None) -> None:
        with self._lock:
            self._queue_connected = False
            self._last_error_code = error_code

    def mark_message_handled(self) -> None:
        with self._lock:
            self._messages_handled += 1

    def snapshot(self) -> RuntimeSnapshot:
        with self._lock:
            return RuntimeSnapshot(
                uptime_seconds=max(0.0, time.monotonic() - self._started_at),
                queue_enabled=self._queue_enabled,
                queue_connected=self._queue_connected,
                messages_handled=self._messages_handled,
                active_jobs=self._active_jobs,
                last_error_code=self._last_error_code,
            )
