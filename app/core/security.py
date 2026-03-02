from dataclasses import dataclass

import httpx
from fastapi import Depends, Header
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCodes


@dataclass
class AuthContext:
    user_id: str
    role: str
    claims: dict


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AppError(ErrorCodes.AUTH_INVALID_TOKEN, "Missing Authorization header", status_code=401)
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AppError(ErrorCodes.AUTH_INVALID_TOKEN, "Invalid Authorization header format", status_code=401)
    return parts[1].strip()


def _jwks_key_for_token(token: str) -> str | None:
    settings = get_settings()
    if not settings.jwks_url:
        return None

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            return None
        response = httpx.get(settings.jwks_url, timeout=3.0)
        response.raise_for_status()
        keys = response.json().get("keys", [])
    except Exception as exc:  # pragma: no cover - network failures are handled as auth errors
        raise AppError(ErrorCodes.AUTH_INVALID_TOKEN, f"Unable to fetch JWKS: {exc}", status_code=401) from exc

    for key in keys:
        if key.get("kid") == kid:
            return key
    return None


def decode_token(token: str) -> dict:
    settings = get_settings()

    key = settings.jwt_secret_key
    algorithms = [settings.jwt_algorithm]

    jwks_key = _jwks_key_for_token(token)
    if jwks_key:
        key = jwks_key
        algorithms = [jwks_key.get("alg") or "RS256"]

    if not key:
        raise AppError(ErrorCodes.AUTH_INVALID_TOKEN, "No JWT verification key configured", status_code=401)

    try:
        return jwt.decode(
            token,
            key,
            algorithms=algorithms,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"verify_at_hash": False},
        )
    except JWTError as exc:
        raise AppError(ErrorCodes.AUTH_INVALID_TOKEN, "Invalid or expired token", status_code=401) from exc


def require_user(authorization: str | None = Header(default=None)) -> AuthContext:
    token = _extract_bearer_token(authorization)
    claims = decode_token(token)
    user_id = claims.get("user_id") or claims.get("sub")
    if not user_id:
        raise AppError(ErrorCodes.AUTH_INVALID_TOKEN, "Token missing user_id claim", status_code=401)
    role = claims.get("role", "user")
    return AuthContext(user_id=user_id, role=role, claims=claims)


def require_admin(user: AuthContext = Depends(require_user)) -> AuthContext:
    if user.role != "admin":
        raise AppError(ErrorCodes.AUTH_FORBIDDEN, "Admin role required", status_code=403)
    return user
