"""X-Request-Id handling (API-004, PG-24)."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from rootline_common.ids import is_ulid, new_ulid
from rootline_common.logging import request_id_var


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        # First x-request-id header; latin-1 never fails to decode (Starlette header encoding, PG-24 D4).
        raw = next((v for k, v in scope["headers"] if k == b"x-request-id"), b"")
        incoming = raw.decode("latin-1")
        rid = incoming if is_ulid(incoming) else new_ulid()
        scope.setdefault("state", {})["request_id"] = rid  # read by the 500 handler (PG-24 D2)
        token = request_id_var.set(rid)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).append((b"x-request-id", rid.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_var.reset(token)
