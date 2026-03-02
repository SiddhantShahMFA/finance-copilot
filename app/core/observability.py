from collections import defaultdict, deque
from threading import Lock
from time import time


class InMemoryObservabilityStore:
    def __init__(self, latency_window: int = 1000):
        self._latency_window = latency_window
        self._started_at = time()
        self._metrics = defaultdict(
            lambda: {
                "request_count": 0,
                "error_count": 0,
                "latencies_ms": deque(maxlen=self._latency_window),
            }
        )
        self._lock = Lock()

    def record(self, method: str, path: str, status_code: int, latency_ms: float) -> None:
        key = f"{method} {path}"
        with self._lock:
            bucket = self._metrics[key]
            bucket["request_count"] += 1
            if status_code >= 400:
                bucket["error_count"] += 1
            bucket["latencies_ms"].append(float(latency_ms))

    def snapshot(self) -> dict:
        with self._lock:
            endpoint_metrics = []
            total_requests = 0
            total_errors = 0

            for key, value in sorted(self._metrics.items()):
                latencies = list(value["latencies_ms"])
                if latencies:
                    latencies_sorted = sorted(latencies)
                    idx = int(0.95 * (len(latencies_sorted) - 1))
                    p95 = latencies_sorted[idx]
                    avg = sum(latencies_sorted) / len(latencies_sorted)
                else:
                    p95 = 0.0
                    avg = 0.0

                total_requests += value["request_count"]
                total_errors += value["error_count"]
                endpoint_metrics.append(
                    {
                        "endpoint": key,
                        "request_count": value["request_count"],
                        "error_count": value["error_count"],
                        "avg_latency_ms": round(avg, 2),
                        "p95_latency_ms": round(p95, 2),
                    }
                )

            return {
                "uptime_seconds": round(time() - self._started_at, 2),
                "total_requests": total_requests,
                "total_errors": total_errors,
                "endpoints": endpoint_metrics,
            }

    def reset(self) -> None:
        with self._lock:
            self._metrics.clear()
            self._started_at = time()


observability_store = InMemoryObservabilityStore()
