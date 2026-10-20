from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import Settings
from app.main import app
from app.services.ai_access import require_ai_access

TOKEN_HASH = "11caa243f14b435cf3723169bb9efe0efb58acf790349ac6780f028b98a7572c"


def request_with(authorization: str | None = None):  # type: ignore[no-untyped-def]
    headers = {} if authorization is None else {"authorization": authorization}
    return SimpleNamespace(headers=headers)


def test_ai_access_accepts_matching_bearer_token() -> None:
    settings = Settings(ai_access_token_hash=TOKEN_HASH, run_worker_enabled=False)
    require_ai_access(request_with("Bearer test-ai-access-token"), settings)


@pytest.mark.parametrize("authorization", [None, "", "Basic value", "Bearer wrong-token"])
def test_ai_access_rejects_missing_or_invalid_token(authorization: str | None) -> None:
    settings = Settings(ai_access_token_hash=TOKEN_HASH, run_worker_enabled=False)
    with pytest.raises(HTTPException) as captured:
        require_ai_access(request_with(authorization), settings)
    assert captured.value.status_code == 401
    assert captured.value.detail["code"] == "AI_ACCESS_DENIED"
    assert captured.value.headers == {"WWW-Authenticate": "Bearer"}


def test_ai_access_fails_closed_without_configured_hash() -> None:
    settings = Settings(ai_access_token_hash=None, run_worker_enabled=False)
    with pytest.raises(HTTPException) as captured:
        require_ai_access(request_with("Bearer test-ai-access-token"), settings)
    assert captured.value.status_code == 503
    assert captured.value.detail["code"] == "AI_ACCESS_NOT_CONFIGURED"


def test_cors_configuration_allows_authorization_header() -> None:
    middleware = next(item for item in app.user_middleware if item.cls is CORSMiddleware)
    assert "Authorization" in middleware.kwargs["allow_headers"]
