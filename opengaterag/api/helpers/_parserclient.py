import asyncio
import json
from typing import Protocol

from fastapi import UploadFile
import httpx

from opengaterag.api.utils.exceptions import FileSizeLimitExceededException


class DocumentParser(Protocol):
    async def parse(self, file: UploadFile, pages: list[int] | None = None) -> str | list[dict]: ...


class ParserClient:
    def __init__(
        self,
        worker_url: str,
        timeout_seconds: float = 120,
        max_input_bytes: int = 20_000_000,
        max_response_bytes: int = 64 * 1024 * 1024,
        max_concurrent: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.worker_url = worker_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_input_bytes = max_input_bytes
        self.max_response_bytes = max_response_bytes
        self.conversion_semaphore = asyncio.Semaphore(value=max_concurrent)
        self.transport = transport

    async def parse(self, file: UploadFile, pages: list[int] | None = None) -> str | list[dict]:
        file.file.seek(0, 2)
        file_size = file.file.tell()
        await file.seek(0)
        if file_size > self.max_input_bytes:
            raise FileSizeLimitExceededException()
        try:
            async with self.conversion_semaphore:
                return await asyncio.wait_for(self._parse_remote(file=file, pages=pages), timeout=self.timeout_seconds)
        except (TimeoutError, httpx.TimeoutException) as e:
            raise TimeoutError("Parser worker timed out") from e
        finally:
            await file.seek(0)

    async def _parse_remote(self, file: UploadFile, pages: list[int] | None) -> str | list[dict]:
        data = {"pages": json.dumps(pages)} if pages is not None else {}
        files = {
            "file": (
                file.filename or "document",
                file.file,
                file.content_type or "application/octet-stream",
            )
        }
        body = bytearray()

        async with httpx.AsyncClient(base_url=self.worker_url, timeout=self.timeout_seconds, transport=self.transport) as client:
            async with client.stream("POST", "/v1/parse", data=data, files=files) as response:
                if response.status_code == 413:
                    raise FileSizeLimitExceededException()
                if response.status_code != 200:
                    raise ValueError(f"Parser worker returned HTTP {response.status_code}")
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > self.max_response_bytes:
                        raise ValueError("Parser worker response exceeds the output-size limit")
                    body.extend(chunk)

        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError("Parser worker returned invalid JSON") from e

        content = payload.get("content") if isinstance(payload, dict) else None
        if isinstance(content, str):
            return content
        if isinstance(content, list) and all(
            isinstance(page, dict) and isinstance(page.get("text"), str) and isinstance(page.get("metadata"), dict) for page in content
        ):
            return content
        raise ValueError("Parser worker returned an invalid document")
