from __future__ import annotations

import hashlib
import secrets

from fastapi import HTTPException, Request

from app.core.settings import Settings

MAX_ACCESS_TOKEN_LENGTH = 512


def require_ai_access(request: Request, settings: Settings) -> None:
    """Authorize an AI request without exposing either configured secret."""
    configured_hash = settings.ai_access_token_hash
    if configured_hash is None:
        raise HTTPException(
            503,
            detail={
                "code": "AI_ACCESS_NOT_CONFIGURED",
                "message": "AI access control is not configured.",
            },
        )

    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not token
        or len(token) > MAX_ACCESS_TOKEN_LENGTH
    ):
        raise _access_denied()

    supplied_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expected_hash = configured_hash.get_secret_value().strip().lower()
    if len(expected_hash) != 64 or not secrets.compare_digest(supplied_hash, expected_hash):
        raise _access_denied()


def _access_denied() -> HTTPException:
    return HTTPException(
        401,
        detail={"code": "AI_ACCESS_DENIED", "message": "A valid AI access token is required."},
        headers={"WWW-Authenticate": "Bearer"},
    )
