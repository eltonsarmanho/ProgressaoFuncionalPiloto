"""Domain error -> HTTP mapping (design.md, Error Handling Strategy)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.use_cases.auth import InvalidCredentials, TooManyAttempts, Unauthenticated
from app.domain.errors import Conflict, Forbidden, NotFound, ValidationFailed

STATUS = (
    (InvalidCredentials, 401),
    (Unauthenticated, 401),
    (Forbidden, 403),
    (NotFound, 404),
    (Conflict, 409),  # includes StaleVersion
    (TooManyAttempts, 429),
)


def _field_errors(errors: list[dict[str, str]]) -> JSONResponse:
    return JSONResponse({"detail": errors}, status_code=422)


def install_error_handlers(app: FastAPI) -> None:
    def make_handler(status: int):
        async def handler(request: Request, exc: Exception) -> JSONResponse:
            return JSONResponse({"detail": str(exc)}, status_code=status)

        return handler

    for exc_type, status in STATUS:
        app.add_exception_handler(exc_type, make_handler(status))

    @app.exception_handler(ValidationFailed)
    async def validation_failed(request: Request, exc: ValidationFailed) -> JSONResponse:
        return _field_errors([{"field": exc.field, "message": exc.message}])

    @app.exception_handler(RequestValidationError)
    async def request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _field_errors(
            [
                {"field": str(err["loc"][-1]) if err["loc"] else "", "message": err["msg"]}
                for err in exc.errors()
            ]
        )
