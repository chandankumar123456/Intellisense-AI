# app/infrastructure/cache_store.py
"""
Caching layer for EviLearn.
Uses Redis for popular queries / passages / verification outputs.
Falls back to in-memory dict if Redis unavailable.
"""

import json
import hashlib
from typing import Any, Optional
from app.core.config import CACHE_PREFIX, CACHE_TTL_SECONDS
from app.core.logging import log_info, log_warning


# Attempt Redis import
_redis_client = None
_memory_cache: dict = {}

try:
    from app.core.redis_client import redis_client as _redis_client
except Exception:
    log_warning("Redis unavailable, using in-memory cache fallback")


def _make_key(key: str) -> str:
    """Prefix and hash the key."""
    return CACHE_PREFIX + hashlib.sha256(key.encode()).hexdigest()[:32]


def cache_get(key: str) -> Optional[Any]:
    """Retrieve cached value."""
    full_key = _make_key(key)

    # Try Redis first
    if _redis_client:
        try:
            raw = _redis_client.get(full_key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass

    # Fallback to memory
    return _memory_cache.get(full_key)


def cache_set(key: str, value: Any, ttl: int = CACHE_TTL_SECONDS):
    """Set a cached value with TTL."""
    full_key = _make_key(key)
    serialized = json.dumps(value, default=str)

    # Try Redis first
    if _redis_client:
        try:
            _redis_client.setex(full_key, ttl, serialized)
            return
        except Exception:
            pass

    # Fallback to memory (no TTL enforcement for simplicity)
    _memory_cache[full_key] = value


def cache_invalidate(key: str):
    """Remove a cached value."""
    full_key = _make_key(key)

    if _redis_client:
        try:
            _redis_client.delete(full_key)
        except Exception:
            pass

    _memory_cache.pop(full_key, None)


def make_claim_cache_key(claim_text: str, evidence_ids: list) -> str:
    """Stable hash of (claim + top evidence ids) for caching verification results."""
    combined = claim_text + "|" + "|".join(sorted(evidence_ids))
    return hashlib.sha256(combined.encode()).hexdigest()
