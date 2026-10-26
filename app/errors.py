"""Errors the apps can understand.

Every error response has the same JSON shape:

    {"error": "kiosk-busy", "message": "Someone else is using this kiosk..."}

`error` is a stable code the phone app maps to a Korean message for the
screen reader; `message` is an English fallback for developers.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


# HTTP status per error code (anything not listed is 400 Bad Request).
_STATUS = {
    "not-signed-in": 401,
    "not-kiosk": 401,
    "token-invalid": 403,
    "not-your-session": 403,
    "not-your-kiosk": 403,
    "kiosk-not-found": 404,
    "store-not-found": 404,
    "session-not-found": 404,
    "order-not-found": 404,
    "unknown-item": 404,
    "kiosk-busy": 409,
    "session-expired": 409,
    "item-unavailable": 409,
    "choice-unavailable": 409,
    "too-late-to-cancel": 409,
    "bad-transition": 409,
}


def status_for(reason: str) -> int:
    return _STATUS.get(reason, 400)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, err: AppError) -> JSONResponse:
        return JSONResponse(status_code=status_for(err.reason), content={"error": err.reason, "message": err.message})

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, err: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": "bad-request", "message": "The request body is invalid.", "details": err.errors()},
        )
