# app/infrastructure/audit_store.py
"""
Audit logging for EviLearn verification pipeline.
Stores full retrieval traces, decisions, and provenance.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any
from app.core.config import AUDIT_LOG_PATH
from app.core.logging import log_info


def _ensure_dir():
    os.makedirs(AUDIT_LOG_PATH, exist_ok=True)


def record_audit(entry: Dict[str, Any]) -> str:
    """
    Save a full trace of retrieval/verification steps and decisions.
    Returns the audit_id.
    """
    _ensure_dir()

    audit_id = entry.get("audit_id") or str(uuid.uuid4())
    entry["audit_id"] = audit_id
    entry["recorded_at"] = datetime.utcnow().isoformat()

    # Sanitize: remove PII if present
    _redact_pii(entry)

    filename = f"{audit_id}.json"
    filepath = os.path.join(AUDIT_LOG_PATH, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2, default=str)

    log_info(f"Audit recorded: {audit_id}")
    return audit_id


def get_audit(audit_id: str) -> Dict[str, Any] | None:
    """Retrieve an audit record by ID."""
    filepath = os.path.join(AUDIT_LOG_PATH, f"{audit_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _redact_pii(entry: Dict[str, Any]):
    """Minimal PII redaction in audit logs."""
    sensitive_keys = {"email", "phone", "password", "ssn", "credit_card"}
    for key in list(entry.keys()):
        if key.lower() in sensitive_keys:
            entry[key] = "[REDACTED]"
