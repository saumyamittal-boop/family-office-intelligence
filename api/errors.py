"""One error shape for the whole API: {"detail": "...", "problems": [...]}. Never echoes request input."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("fo.api")


class ApiError(Exception):
    def __init__(self, status: int, detail: str, problems: list[str] | None = None, headers: dict | None = None):
        self.status, self.detail, self.problems, self.headers = status, detail, problems, headers or {}


def _body(detail: str, problems: list[str] | None = None) -> dict:
    return {"detail": detail, "problems": problems}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, err: ApiError):
        return JSONResponse(_body(err.detail, err.problems), status_code=err.status, headers=err.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, err: StarletteHTTPException):
        return JSONResponse(_body(str(err.detail)), status_code=err.status_code, headers=getattr(err, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, err: RequestValidationError):
        # Field names and rules only: the submitted values are deliberately left out.
        problems = [f"{'.'.join(str(p) for p in e['loc'][1:]) or 'request'}: {e['msg']}" for e in err.errors()][:20]
        return JSONResponse(_body("The request was not valid.", problems), status_code=422)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, err: Exception):
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(_body("Something went wrong on our side."), status_code=500)
