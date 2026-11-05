from fastapi import FastAPI, File, UploadFile
import pytest
from starlette.responses import JSONResponse

from opengaterag.api.utils.requestlimits import RequestBodyLimitMiddleware


async def exercise_middleware(messages, headers=None, path="/v1/documents"):
    sent_messages = []
    downstream_called = False
    pending_messages = list(messages)

    async def downstream(scope, receive, send):
        nonlocal downstream_called
        downstream_called = True
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if not message.get("more_body", False):
                break
        await JSONResponse({"status": "accepted"})(scope, receive, send)

    async def receive():
        if pending_messages:
            return pending_messages.pop(0)
        return {"type": "http.disconnect"}

    async def send(message):
        sent_messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "root_path": "",
        "query_string": b"",
        "headers": headers or [],
    }
    middleware = RequestBodyLimitMiddleware(downstream, max_body_bytes=5)
    await middleware(scope, receive, send)
    return sent_messages, downstream_called


@pytest.mark.asyncio
async def test_content_length_over_limit_is_rejected_before_downstream():
    messages, downstream_called = await exercise_middleware(
        [{"type": "http.request", "body": b"123456", "more_body": False}],
        headers=[(b"content-length", b"6")],
    )

    assert messages[0]["status"] == 413
    assert downstream_called is False


@pytest.mark.asyncio
async def test_streaming_body_over_limit_is_rejected_without_content_length():
    messages, downstream_called = await exercise_middleware(
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"456", "more_body": False},
        ]
    )

    assert messages[0]["status"] == 413
    assert downstream_called is True


@pytest.mark.asyncio
async def test_body_within_limit_reaches_downstream():
    messages, downstream_called = await exercise_middleware([{"type": "http.request", "body": b"12345", "more_body": False}])

    assert messages[0]["status"] == 200
    assert downstream_called is True


@pytest.mark.asyncio
async def test_chunked_multipart_over_limit_returns_413_from_fastapi():
    app = FastAPI()

    @app.post("/v1/documents")
    async def upload(file: UploadFile = File(...)):
        return JSONResponse({"filename": file.filename})

    app.add_middleware(RequestBodyLimitMiddleware, max_body_bytes=64)
    boundary = "parser-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="notes.txt"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "this multipart document exceeds the request body limit\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    messages = [
        {"type": "http.request", "body": body[:40], "more_body": True},
        {"type": "http.request", "body": body[40:], "more_body": False},
    ]
    sent_messages = []

    async def receive():
        if messages:
            return messages.pop(0)
        return {"type": "http.disconnect"}

    async def send(message):
        sent_messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/v1/documents",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"content-type", f"multipart/form-data; boundary={boundary}".encode())],
    }
    await app(scope, receive, send)

    assert sent_messages[0]["status"] == 413
