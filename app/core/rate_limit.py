from collections import defaultdict, deque
from threading import Lock
from time import time


class InMemoryRateLimiter:
    def __init__(self, requests: int, window_seconds: int):
        self.requests = requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time()
        window_start = now - self.window_seconds
        with self._lock:
            queue = self._events[key]
            while queue and queue[0] < window_start:
                queue.popleft()
            if len(queue) >= self.requests:
                return False
            queue.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
