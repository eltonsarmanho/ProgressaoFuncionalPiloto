"""PII-free logging (AUD-04): access records hold only ids, route templates and status codes."""

import logging
import time

from fastapi import FastAPI, Request

ACCESS_LOGGER = "app.access"
FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging() -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format=FORMAT)
    logging.getLogger(ACCESS_LOGGER).setLevel(logging.INFO)
    # SQLAlchemy at INFO logs statement parameters (names, SIAPE). It defaults to WARN;
    # pin it so an external log config cannot turn it on.
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    # Uvicorn's access log prints raw paths and query strings; ours replaces it.
    logging.getLogger("uvicorn.access").disabled = True


def install_access_log(app: FastAPI) -> None:
    """Register last so it wraps every other middleware (401/403 responses included)."""
    logger = logging.getLogger(ACCESS_LOGGER)

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            user = getattr(request.state, "user", None)
            fields = {
                "method": request.method,
                "route": getattr(route, "path", None),
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                "user_id": str(user.id) if user is not None else None,
            }
            logger.info(
                "%(method)s %(route)s %(status)s %(duration_ms)sms user_id=%(user_id)s",
                fields,
                extra=fields,
            )
