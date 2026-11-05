import asyncio
from io import BytesIO

from fastapi import UploadFile
import httpx
import pytest
from starlette.datastructures import Headers

from opengaterag.api.helpers._parserclient import ParserClient
from opengaterag.api.utils.exceptions import FileSizeLimitExceededException


def make_upload(content: bytes = b"plain text") -> UploadFile:
    return UploadFile(filename="notes.txt", file=BytesIO(content), headers=Headers({"content-type": "text/plain"}))


@pytest.mark.asyncio
async def test_parse_streams_upload_and_restores_file_position():
    async def handler(request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        assert request.url.path == "/v1/parse"
        assert b'filename="notes.txt"' in body
        assert b"plain text" in body
        return httpx.Response(200, json={"content": [{"text": "page text", "metadata": {"page": 1}}]})

    upload = make_upload()
    parser = ParserClient("http://parser:8001", transport=httpx.MockTransport(handler))

    parsed = await parser.parse(upload, pages=[0])

    assert parsed == [{"text": "page text", "metadata": {"page": 1}}]
    assert await upload.read() == b"plain text"


@pytest.mark.asyncio
async def test_parse_enforces_response_size_limit():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"content": "this response is too large"})

    parser = ParserClient("http://parser:8001", max_response_bytes=16, transport=httpx.MockTransport(handler))

    with pytest.raises(ValueError, match="output-size limit"):
        await parser.parse(make_upload())


@pytest.mark.asyncio
async def test_parse_rejects_worker_failure():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "unavailable"})

    parser = ParserClient("http://parser:8001", transport=httpx.MockTransport(handler))

    with pytest.raises(ValueError, match="HTTP 503"):
        await parser.parse(make_upload())


@pytest.mark.asyncio
async def test_parse_preflight_rejects_oversized_upload_without_network():
    called = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"content": "unexpected"})

    parser = ParserClient("http://parser:8001", max_input_bytes=4, transport=httpx.MockTransport(handler))

    with pytest.raises(FileSizeLimitExceededException):
        await parser.parse(make_upload())
    assert called is False


@pytest.mark.asyncio
async def test_parse_propagates_worker_size_rejection():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(413, json={"detail": "too large"})

    parser = ParserClient("http://parser:8001", transport=httpx.MockTransport(handler))

    with pytest.raises(FileSizeLimitExceededException):
        await parser.parse(make_upload())


@pytest.mark.asyncio
async def test_parse_enforces_total_timeout():
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, json={"content": "too late"})

    parser = ParserClient("http://parser:8001", timeout_seconds=0.01, transport=httpx.MockTransport(handler))

    with pytest.raises(TimeoutError, match="timed out"):
        await parser.parse(make_upload())
