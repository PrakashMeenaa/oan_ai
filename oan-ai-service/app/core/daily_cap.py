import threading
from datetime import datetime, timezone


class DailyCap:
    """In-memory count of chat requests per UTC day. Resets on restart."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day = ""
        self._count = 0

    def try_acquire(self, cap: int) -> bool:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            if today != self._day:
                self._day, self._count = today, 0
            if self._count >= cap:
                return False
            self._count += 1
            return True

    def reset(self) -> None:
        with self._lock:
            self._day, self._count = "", 0


daily_cap = DailyCap()
