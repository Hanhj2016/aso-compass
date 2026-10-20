import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.api.routes import router
from app.core.settings import get_settings
from app.db.session import engine
from app.services.runs import RunWorker, recover_stale_runs

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    settings = get_settings()
    with Session(engine) as session:
        recover_stale_runs(session, settings.app_env)
    app.state.run_worker = RunWorker(settings)
    yield
    app.state.run_worker.shutdown()


settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)


@app.middleware("http")
async def request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
    identifier = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = identifier
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 65_536:
        return JSONResponse(
            status_code=413,
            content={
                "code": "REQUEST_TOO_LARGE",
                "message": "Request body exceeds 64 KiB.",
                "request_id": identifier,
            },
            headers={"X-Request-ID": identifier},
        )
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request error request_id=%s path=%s", identifier, request.url.path)
        response = JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "The request could not be completed.",
                "request_id": identifier,
            },
        )
    response.headers["X-Request-ID"] = identifier
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


# CORS must wrap the request/error middleware so even safe 500 responses carry
# the allowed-origin header instead of appearing as a browser network failure.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

app.include_router(router)
