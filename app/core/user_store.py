# app/core/user_store.py

import uuid
import time
from app.core.redis_client import redis_client
from app.core.auth_utils import hash_password, verify_password
from app.core.logging import log_info, log_error

# ── Login rate limiting ──
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60  # 15 minutes


def create_user(username: str, password: str, role: str = "user"):
    """
    Create user and store:
    user:<user_id> with {username, password, role, created_at}
    And a lookup: username:<username> = user_id
    """
    if redis_client.exists(f"username:{username}"):
        return None, "Username already exists"

    user_id = str(uuid.uuid4())
    redis_client.hset(f"user:{user_id}", mapping={
        "username": username,
        "password": hash_password(password),
        "role": role,
        "created_at": str(int(time.time())),
    })

    redis_client.set(f"username:{username}", user_id)
    log_info(f"User created: {username} (role={role})")
    return user_id, None


def authenticate_user(username: str, password: str):
    """
    Check if username exists, is not locked out, and password matches.
    Returns (user_id, error) tuple.
    """
    # Check lockout
    lockout_key = f"login_lockout:{username}"
    if redis_client.exists(lockout_key):
        ttl = redis_client.ttl(lockout_key)
        log_error(f"Login attempt for locked account: {username}")
        return None, f"Account temporarily locked. Try again in {ttl // 60} minutes."

    user_id = redis_client.get(f"username:{username}")

    if not user_id:
        _record_failed_login(username)
        return None, "User not found"

    data = redis_client.hgetall(f"user:{user_id}")
    if not verify_password(password, data["password"]):
        _record_failed_login(username)
        return None, "Incorrect password"

    # Clear failed attempts on success
    redis_client.delete(f"login_attempts:{username}")
    log_info(f"Successful login: {username}")
    return user_id, None


def get_user_role(user_id: str) -> str:
    """Get the role of a user. Backfills 'user' if role field is missing (legacy accounts)."""
    role = redis_client.hget(f"user:{user_id}", "role")
    if not role:
        # Backfill for users created before role system was added
        if redis_client.exists(f"user:{user_id}"):
            redis_client.hset(f"user:{user_id}", "role", "user")
            log_info(f"Backfilled role=user for legacy user {user_id}")
        return "user"
    return role


def set_user_role(user_id: str, role: str) -> bool:
    """Set the role of a user. Returns True on success."""
    if not redis_client.exists(f"user:{user_id}"):
        return False
    redis_client.hset(f"user:{user_id}", "role", role)
    username = redis_client.hget(f"user:{user_id}", "username")
    log_info(f"Role updated: {username} -> {role}")
    return True


def _record_failed_login(username: str):
    """Track failed login attempts and lock out after threshold."""
    attempts_key = f"login_attempts:{username}"
    attempts = redis_client.incr(attempts_key)
    redis_client.expire(attempts_key, LOGIN_LOCKOUT_SECONDS)

    log_error(f"Failed login attempt {attempts}/{LOGIN_MAX_ATTEMPTS} for: {username}")

    if attempts >= LOGIN_MAX_ATTEMPTS:
        lockout_key = f"login_lockout:{username}"
        redis_client.setex(lockout_key, LOGIN_LOCKOUT_SECONDS, "locked")
        redis_client.delete(attempts_key)
        log_error(f"Account locked out: {username} ({LOGIN_LOCKOUT_SECONDS}s)")


def get_user_id_by_username(username: str) -> str | None:
    """Look up a user_id by username."""
    return redis_client.get(f"username:{username}")


def set_user_role_by_username(username: str, role: str) -> bool:
    """Set role by username (convenience wrapper)."""
    user_id = get_user_id_by_username(username)
    if not user_id:
        return False
    return set_user_role(user_id, role)