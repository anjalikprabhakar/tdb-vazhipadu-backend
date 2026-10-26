from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

REQUEST_LOCATIONS = {"body", "query", "path", "header", "cookie"}


class AppError(Exception):
    status_code: int = HTTPStatus.BAD_REQUEST
    code: str = "bad_request"

    def __init__(self, message: str, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundError(AppError):
    status_code = HTTPStatus.NOT_FOUND
    code = "not_found"

    def __init__(self, resource: str, resource_id: int) -> None:
        super().__init__(f"{resource} {resource_id} not found")


class ConflictError(AppError):
    status_code = HTTPStatus.CONFLICT
    code = "conflict"


class DailyLimitExceededError(AppError):
    status_code = HTTPStatus.CONFLICT
    code = "daily_limit_exceeded"

    def __init__(self, details: list[dict[str, Any]]) -> None:
        super().__init__("Some offerings do not have enough capacity on this date", details)


class BusinessRuleError(AppError):
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY

    def __init__(
        self, code: str, message: str, details: list[dict[str, Any]] | None = None
    ) -> None:
        super().__init__(message, details)
        self.code = code


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or []}},
        headers=headers,
    )


def _field_path(loc: tuple[int | str, ...]) -> str:
    parts = loc[1:] if loc and loc[0] in REQUEST_LOCATIONS else loc
    return ".".join(str(part) for part in parts)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": _field_path(tuple(error["loc"])), "message": error["msg"]}
            for error in exc.errors()
        ]
        return error_response(
            HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Request is invalid", details
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        status = HTTPStatus(exc.status_code)
        message = exc.detail if isinstance(exc.detail, str) else status.phrase
        return error_response(
            status, status.phrase.lower().replace(" ", "_"), message, headers=exc.headers
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
        return error_response(
            HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", "An unexpected error occurred"
        )
