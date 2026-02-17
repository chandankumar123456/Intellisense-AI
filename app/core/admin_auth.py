# app/core/admin_auth.py
"""
Admin authentication dependency for FastAPI.
Verifies JWT token and checks for admin role.
Logs all admin access attempts.
"""

import os
import json
import time
from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth_utils import decode_jwt_token
from app.core.logging import log_info, log_error

security = HTTPBearer()

ADMIN_AUDIT_PATH = os.path.join("data", "admin_audit")
os.makedirs(ADMIN_AUDIT_PATH, exist_ok=True)


def _log_admin_access(user_id: str, username: str, action: str, success: bool, detail: str = ""):
    """Log admin access attempt to audit file."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "user_id": user_id,
        "username": username,
        "action": action,
        "success": success,
        "detail": detail,
    }
    try:
        log_path = os.path.join(ADMIN_AUDIT_PATH, "admin_access.jsonl")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log_error(f"Failed to write admin audit log: {e}")

    level = "INFO" if success else "WARNING"
    log_info(f"[ADMIN_AUDIT] [{level}] user={username} action={action} success={success} {detail}")


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI dependency that enforces admin-only access.
    Returns the decoded JWT payload if the user is an admin.
    Raises 401 for invalid/missing tokens, 403 for non-admin users.
    """
    token = credentials.credentials
    decoded = decode_jwt_token(token)

    if not decoded:
        _log_admin_access("unknown", "unknown", "admin_access", False, "invalid_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decoded.get("user_id", "unknown")
    username = decoded.get("username", "unknown")
    role = decoded.get("role", "user")

    if role != "admin":
        _log_admin_access(user_id, username, "admin_access", False, f"insufficient_role={role}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. Your role does not have permission.",
        )

    _log_admin_access(user_id, username, "admin_access", True)
    return decoded
