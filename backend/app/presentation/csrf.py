"""Session authentication and CSRF middleware (AUTH-03, AUTH-05, AUTH-06; AD-003)."""

import secrets

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.application.use_cases.auth import Unauthenticated

SESSION_COOKIE = "session"
CSRF_HEADER = "X-CSRF-Token"
PUBLIC_PATHS = frozenset({"/api/health", "/api/auth/login"})
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def install_auth_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"
        if not path.startswith("/api") or path in PUBLIC_PATHS:
            return await call_next(request)

        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return JSONResponse({"detail": "Não autenticado"}, status_code=401)
        container = request.app.state.container
        try:
            session, user = await run_in_threadpool(container.current_session.execute, token)
        except Unauthenticated:
            return JSONResponse({"detail": "Não autenticado"}, status_code=401)

        if request.method in WRITE_METHODS:
            sent = request.headers.get(CSRF_HEADER, "")
            if not secrets.compare_digest(sent.encode(), session.csrf_token.encode()):
                return JSONResponse({"detail": "Token CSRF ausente ou inválido"}, status_code=403)

        request.state.session = session
        request.state.user = user
        return await call_next(request)
