# app/student_knowledge/metrics.py
"""
Lightweight in-process metrics for Student Knowledge pipeline.
Thread-safe counters for observability and health monitoring.
"""

import threading
import time
from typing import Dict, Any


class _Metrics:
    """Thread-safe singleton for pipeline metrics."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._counters: Dict[str, float] = {
            "ingest_total": 0,
            "ingest_success": 0,
            "ingest_fail": 0,
            "ingest_duplicate": 0,
            "ingest_partial": 0,
            "embed_calls": 0,
            "embed_failures": 0,
            "validation_fail": 0,
            "ingest_latency_sum_ms": 0,
            "embed_latency_sum_ms": 0,
            "queue_size": 0,
            "reindex_backoff_skipped": 0,
            "reindex_exhausted": 0,
            "drift_detected": 0,
            "repair_throttled": 0,
            "model_migration_needed": 0,
        }
        self._lock_counter = threading.Lock()
        self._start_time = time.time()
        self._initialized = True

    def inc(self, name: str, value: float = 1.0):
        """Increment a counter."""
        with self._lock_counter:
            self._counters[name] = self._counters.get(name, 0) + value

    def dec(self, name: str, value: float = 1.0):
        """Decrement a counter."""
        with self._lock_counter:
            self._counters[name] = max(0, self._counters.get(name, 0) - value)

    def set_val(self, name: str, value: float):
        """Set a counter to a specific value."""
        with self._lock_counter:
            self._counters[name] = value

    def get_all(self) -> Dict[str, Any]:
        """Get all metrics with computed rates."""
        with self._lock_counter:
            snapshot = dict(self._counters)

        uptime = max(time.time() - self._start_time, 1)
        total = max(snapshot.get("ingest_total", 0), 1)

        snapshot["uptime_seconds"] = round(uptime, 1)
        snapshot["success_rate"] = round(snapshot.get("ingest_success", 0) / total, 3)
        snapshot["fail_rate"] = round(snapshot.get("ingest_fail", 0) / total, 3)
        snapshot["ingest_rate_per_min"] = round(snapshot.get("ingest_total", 0) / (uptime / 60), 2)
        snapshot["avg_ingest_latency_ms"] = round(
            snapshot.get("ingest_latency_sum_ms", 0) / max(snapshot.get("ingest_success", 0), 1), 1
        )
        snapshot["avg_embed_latency_ms"] = round(
            snapshot.get("embed_latency_sum_ms", 0) / max(snapshot.get("embed_calls", 0), 1), 1
        )

        return snapshot


# Module-level singleton
metrics = _Metrics()
