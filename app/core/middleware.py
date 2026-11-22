import logging
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.constants import MAX_REQUEST_ID_LENGTH, REQUEST_ID_HEADER

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        supplied = Headers(scope=scope).get(REQUEST_ID_HEADER, "")
        request_id = (
            supplied
            if supplied
            and supplied.isprintable()
            and len(supplied) <= MAX_REQUEST_ID_LENGTH
            else str(uuid4())
        )
        scope.setdefault("state", {})["request_id"] = request_id
        started = perf_counter()
        status_code = 500
        response_elapsed = None

        async def send_response(message: Message) -> None:
            nonlocal status_code, response_elapsed
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            if message["type"] == "http.response.body" and not message.get(
                "more_body", False
            ):
                response_elapsed = (perf_counter() - started) * 1000
            await send(message)

        try:
            await self.app(scope, receive, send_response)
        finally:
            elapsed = (
                response_elapsed
                if response_elapsed is not None
                else (perf_counter() - started) * 1000
            )
            logger.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
                request_id,
                scope["method"],
                scope["path"],
                status_code,
                elapsed,
                extra={
                    "request_id": request_id,
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": elapsed,
                },
            )
