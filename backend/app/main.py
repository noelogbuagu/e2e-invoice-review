from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.accounting.routes import router as accounting_router
from app.auth.routes import router as auth_router
from app.auth.session import is_authenticated
from app.config import APP_CONFIG, get_settings
from app.correction_email.routes import router as email_event_router
from app.database import build_database
from app.documents.models import DocumentRecord
from app.documents.routes import router as document_router


class AccessPasswordMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        if not settings.auth_enabled:
            return await call_next(request)

        path = request.url.path
        if path == "/health" or path.startswith("/api/auth/") or not path.startswith("/api/"):
            return await call_next(request)

        if not is_authenticated(request, settings):
            return JSONResponse(status_code=401, content={"detail": "Authentication required"})
        return await call_next(request)


def create_app() -> FastAPI:
    config = APP_CONFIG
    config.upload_dir.mkdir(parents=True, exist_ok=True)
    database_path = config.database_url.removeprefix("sqlite:///")
    if config.database_url.startswith("sqlite:///"):
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

    engine, session_factory = build_database(config.database_url)
    DocumentRecord.metadata.create_all(engine)

    settings = get_settings()
    app = FastAPI(title="Invoice Review API", version="0.1.0")
    app.state.config = config
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.add_middleware(AccessPasswordMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(document_router)
    app.include_router(accounting_router)
    app.include_router(email_event_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    frontend_dist = settings.resolve_frontend_dist()
    if frontend_dist is not None:
        assets = frontend_dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{full_path:path}")
        def spa_fallback(full_path: str) -> FileResponse:
            root = frontend_dist.resolve()
            candidate = (root / full_path).resolve()
            if full_path and candidate.is_file() and candidate.is_relative_to(root):
                return FileResponse(candidate)
            return FileResponse(root / "index.html")

    return app
