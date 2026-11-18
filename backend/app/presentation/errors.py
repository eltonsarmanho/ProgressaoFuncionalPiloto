"""Domain error -> HTTP mapping (design.md, Error Handling Strategy)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.use_cases.auth import InvalidCredentials, TooManyAttempts, Unauthenticated
from app.domain.errors import (
    Conflict,
    Forbidden,
    GenerationRefused,
    Gone,
    NotFound,
    ValidationFailed,
)

STATUS = (
    (InvalidCredentials, 401),
    (Unauthenticated, 401),
    (Forbidden, 403),
    (NotFound, 404),
    (TooManyAttempts, 429),
)


GENERATION_FIELD = "geracao"
FILE_FIELD = "arquivo"


def _coded(status: int, field: str, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"detail": [{"field": field, "code": code, "message": message}]}, status_code=status
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

    @app.exception_handler(Conflict)  # 409; includes StaleVersion
    async def conflict(request: Request, exc: Conflict) -> JSONResponse:
        body: dict[str, str] = {"detail": str(exc)}
        if exc.code is not None:
            body["code"] = exc.code
        return JSONResponse(body, status_code=409)

    @app.exception_handler(GenerationRefused)
    async def generation_refused(request: Request, exc: GenerationRefused) -> JSONResponse:
        return _coded(422, GENERATION_FIELD, exc.code, exc.message)

    @app.exception_handler(Gone)
    async def gone(request: Request, exc: Gone) -> JSONResponse:
        return _coded(410, FILE_FIELD, exc.code, exc.message)

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
