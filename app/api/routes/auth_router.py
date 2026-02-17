# app/api/routes/auth_router.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.auth_utils import create_jwt_token, decode_jwt_token
from app.core.user_store import (
    create_user, authenticate_user, get_user_role, set_user_role,
    get_user_id_by_username, set_user_role_by_username,
)
from app.core.admin_auth import require_admin
from app.core.logging import log_info

security = HTTPBearer()
router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    username: str
    token: str
    role: str


class PromoteRequest(BaseModel):
    user_id: str
    role: str  # "admin" or "user"


@router.post("/signup", response_model=AuthResponse)
async def signup(payload: SignupRequest):
    user_id, error = create_user(payload.username, payload.password)
    if error:
        raise HTTPException(400, detail=error)

    role = get_user_role(user_id)
    token = create_jwt_token(user_id, payload.username, role)

    return AuthResponse(
        user_id=user_id,
        username=payload.username,
        token=token,
        role=role,
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    user_id, error = authenticate_user(payload.username, payload.password)
    if error:
        raise HTTPException(400, error)

    role = get_user_role(user_id)
    token = create_jwt_token(user_id, payload.username, role)

    return AuthResponse(
        user_id=user_id,
        username=payload.username,
        token=token,
        role=role,
    )


@router.get("/me")
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    decoded = decode_jwt_token(token)

    if not decoded:
        raise HTTPException(status_code=401, detail="Invalid token")

    return decoded


@router.post("/promote")
async def promote_user(
    payload: PromoteRequest,
    admin: dict = Depends(require_admin),
):
    """Promote or demote a user. Admin-only endpoint."""
    if payload.role not in ("admin", "user"):
        raise HTTPException(400, "Role must be 'admin' or 'user'")

    success = set_user_role(payload.user_id, payload.role)
    if not success:
        raise HTTPException(404, "User not found")

    log_info(f"Admin {admin['username']} set user {payload.user_id} role to {payload.role}")

    return {
        "status": "updated",
        "user_id": payload.user_id,
        "new_role": payload.role,
        "promoted_by": admin["username"],
    }


@router.post("/promote-by-username")
async def promote_user_by_username(
    payload: dict,
    admin: dict = Depends(require_admin),
):
    """Promote/demote a user by username. Admin-only."""
    username = payload.get("username")
    role = payload.get("role", "admin")
    if not username:
        raise HTTPException(400, "username is required")
    if role not in ("admin", "user"):
        raise HTTPException(400, "Role must be 'admin' or 'user'")

    user_id = get_user_id_by_username(username)
    if not user_id:
        raise HTTPException(404, f"User '{username}' not found")

    success = set_user_role(user_id, role)
    if not success:
        raise HTTPException(500, "Failed to update role")

    log_info(f"Admin {admin['username']} set {username} (id={user_id}) role to {role}")
    return {"status": "updated", "username": username, "user_id": user_id, "new_role": role}


@router.get("/lookup/{username}")
async def lookup_user(username: str, admin: dict = Depends(require_admin)):
    """Look up a user_id by username. Admin-only."""
    user_id = get_user_id_by_username(username)
    if not user_id:
        raise HTTPException(404, f"User '{username}' not found")
    role = get_user_role(user_id)
    return {"username": username, "user_id": user_id, "role": role}