# app/rag/retrieval_memory.py
"""
Long-Term Retrieval Memory.

SQLite-backed pattern tracker that learns from past retrieval outcomes:
  - Records: query_type → chunk_types → confidence → outcome quality
  - Provides: boost multipliers + threshold hints for future queries
  - Decays: entries older than configured days get exponentially decayed

Table: retrieval_outcomes
  query_hash     TEXT     — SHA256 of normalized query
  query_type     TEXT     — CONCEPTUAL, FACTUAL, etc.
  chunk_types    TEXT     — JSON list of chunk section_types used
  confidence     REAL     — final retrieval confidence score
  recommendation TEXT     — proceed/expand/retry/grounded_only
  outcome_quality REAL    — 0-1 outcome quality (from synthesis confidence)
  timestamp      TEXT     — ISO timestamp
"""

import hashlib
import json
import math
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter

from app.core.config import (
    RETRIEVAL_MEMORY_DB_PATH,
    RETRIEVAL_MEMORY_DECAY_DAYS,
)
from app.core.logging import log_info, log_warning


_DB_INIT_SQL = """
CREATE TABLE IF NOT EXISTS retrieval_outcomes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash      TEXT    NOT NULL,
    query_type      TEXT    NOT NULL DEFAULT 'general',
    chunk_types     TEXT    NOT NULL DEFAULT '[]',
    confidence      REAL    NOT NULL DEFAULT 0.0,
    recommendation  TEXT    NOT NULL DEFAULT 'proceed',
    outcome_quality REAL    NOT NULL DEFAULT 0.0,
    timestamp       TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ro_query_type ON retrieval_outcomes(query_type);
CREATE INDEX IF NOT EXISTS idx_ro_timestamp  ON retrieval_outcomes(timestamp);
"""


class RetrievalMemory:
    """
    Singleton-style retrieval memory backed by SQLite.
    Thread-safe for concurrent reads; writes are serialized by SQLite.
    """

    def __init__(self, db_path: str = RETRIEVAL_MEMORY_DB_PATH):
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DB_INIT_SQL)
        self._conn.commit()

    def record_outcome(
        self,
        query: str,
        query_type: str,
        chunk_types: List[str],
        confidence: float,
        recommendation: str,
        outcome_quality: float,
    ) -> None:
        """Record a retrieval outcome for learning."""
        try:
            qhash = self._hash_query(query)
            self._conn.execute(
                """INSERT INTO retrieval_outcomes
                   (query_hash, query_type, chunk_types, confidence, recommendation, outcome_quality, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    qhash,
                    query_type,
                    json.dumps(chunk_types),
                    confidence,
                    recommendation,
                    outcome_quality,
                    datetime.utcnow().isoformat(),
                ),
            )
            self._conn.commit()
        except Exception as e:
            log_warning(f"RetrievalMemory.record_outcome failed: {e}")

    def get_boosts(self, query_type: str) -> Dict[str, float]:
        """
        Return chunk-type boost multipliers learned from past successes.

        Returns dict like {"definition": 1.2, "body": 0.9, ...}
        meaning 'definition' chunks historically correlate with good outcomes
        for this query type.
        """
        try:
            cutoff = (datetime.utcnow() - timedelta(days=RETRIEVAL_MEMORY_DECAY_DAYS)).isoformat()
            rows = self._conn.execute(
                """SELECT chunk_types, confidence, outcome_quality, timestamp
                   FROM retrieval_outcomes
                   WHERE query_type = ? AND timestamp > ?
                   ORDER BY timestamp DESC
                   LIMIT 100""",
                (query_type, cutoff),
            ).fetchall()

            if len(rows) < 3:
                return {}  # Not enough data

            # Aggregate: weight each entry by outcome quality * decay
            type_scores: Dict[str, float] = Counter()
            type_counts: Dict[str, int] = Counter()

            now = datetime.utcnow()
            for row in rows:
                chunk_types = json.loads(row["chunk_types"])
                quality = row["outcome_quality"]
                ts = datetime.fromisoformat(row["timestamp"])
                age_days = (now - ts).days
                decay = math.exp(-age_days / max(RETRIEVAL_MEMORY_DECAY_DAYS, 1))

                weight = quality * decay
                for ct in set(chunk_types):
                    type_scores[ct] += weight
                    type_counts[ct] += 1

            # Normalize to boost multipliers (centered around 1.0)
            if not type_scores:
                return {}

            avg_score = sum(type_scores.values()) / max(len(type_scores), 1)
            boosts = {}
            for ct, score in type_scores.items():
                if type_counts[ct] >= 2:
                    ratio = score / max(avg_score, 0.01)
                    boosts[ct] = round(min(1.5, max(0.5, ratio)), 3)

            log_info(f"RetrievalMemory boosts for '{query_type}': {boosts}")
            return boosts

        except Exception as e:
            log_warning(f"RetrievalMemory.get_boosts failed: {e}")
            return {}

    def get_threshold_hints(self, query_type: str) -> Optional[Tuple[float, float]]:
        """
        Return suggested (high_threshold, low_threshold) based on historical
        confidence distribution for successful queries of this type.

        Returns None if insufficient data.
        """
        try:
            cutoff = (datetime.utcnow() - timedelta(days=RETRIEVAL_MEMORY_DECAY_DAYS)).isoformat()
            rows = self._conn.execute(
                """SELECT confidence, outcome_quality
                   FROM retrieval_outcomes
                   WHERE query_type = ? AND timestamp > ? AND outcome_quality > 0.5
                   ORDER BY timestamp DESC
                   LIMIT 50""",
                (query_type, cutoff),
            ).fetchall()

            if len(rows) < 5:
                return None   # Not enough successful data

            confidences = [r["confidence"] for r in rows]
            avg_conf = sum(confidences) / len(confidences)

            # Set high threshold just below average successful confidence
            # Set low threshold at 50% of high
            high = round(min(0.85, max(0.50, avg_conf * 0.95)), 3)
            low = round(max(0.20, high * 0.50), 3)

            log_info(f"RetrievalMemory thresholds for '{query_type}': high={high}, low={low}")
            return (high, low)

        except Exception as e:
            log_warning(f"RetrievalMemory.get_threshold_hints failed: {e}")
            return None

    def cleanup_old(self, days: int = None) -> int:
        """Remove entries older than configured days. Returns count deleted."""
        days = days or RETRIEVAL_MEMORY_DECAY_DAYS * 3  # Keep 3x decay window
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        try:
            cur = self._conn.execute(
                "DELETE FROM retrieval_outcomes WHERE timestamp < ?", (cutoff,)
            )
            self._conn.commit()
            return cur.rowcount
        except Exception as e:
            log_warning(f"RetrievalMemory.cleanup_old failed: {e}")
            return 0

    @staticmethod
    def _hash_query(query: str) -> str:
        normalized = query.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]


# Singleton instance
_memory_instance: Optional[RetrievalMemory] = None


def get_retrieval_memory() -> RetrievalMemory:
    """Get or create the singleton RetrievalMemory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = RetrievalMemory()
    return _memory_instance
