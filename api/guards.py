"""Request-size and content-type guards, enforced on the bytes that actually arrive.

Reading `Content-Length` is not enough: a client can send a chunked body that declares no length at all. This is a plain ASGI middleware that
reads the body itself, up to the limit, and only then hands it on: an oversized body is answered with 413 without the application ever seeing it,
and memory use is bounded by the limit. Answers use the API's one error shape.
"""
from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

UNSAFE = frozenset({"POST", "PUT", "PATCH", "DELETE"})
TOO_LARGE = "That request is too large."
NOT_JSON = "Send JSON."


def _refusal(status: int, detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail, "problems": None}, status_code=status)


class BodyGuard:
    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in UNSAFE:
            await self.app(scope, receive, send)
            return
        headers = {name.lower(): value for name, value in scope["headers"]}
        declared = headers.get(b"content-length", b"0")
        length = int(declared) if declared.isdigit() else 0
        chunked = b"chunked" in headers.get(b"transfer-encoding", b"").lower()
        if length > self.max_bytes:  # decided before anything is read
            await _refusal(413, TOO_LARGE)(scope, receive, send)
            return
        if not (length > 0 or chunked):  # no body to guard
            await self.app(scope, receive, send)
            return
        if not headers.get(b"content-type", b"").lower().startswith(b"application/json"):
            await _refusal(415, NOT_JSON)(scope, receive, send)
            return

        # Read the body here, counting as it arrives, so a chunked upload cannot slip past a limit that only trusts the header.
        held: list[Message] = []
        received = 0
        while True:
            message = await receive()
            held.append(message)
            if message["type"] != "http.request":  # the client went away
                break
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                await _refusal(413, TOO_LARGE)(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        replayed = 0

        async def replay() -> Message:
            nonlocal replayed
            if replayed < len(held):
                replayed += 1
                return held[replayed - 1]
            return await receive()

        await self.app(scope, replay, send)
