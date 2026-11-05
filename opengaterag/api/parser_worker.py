import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import tempfile
from typing import BinaryIO

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from opengaterag.api.helpers._parser_process import ParserProcessRequest, run_isolated

logger = logging.getLogger(__name__)


def _environment_int(name: str, default: int) -> int:
    value = int(os.environ.get(name, default))
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class ParserWorkerSettings:
    max_concurrent: int = 2
    timeout_seconds: int = 120
    process_cpu_seconds: int = 120
    process_memory_bytes: int = 1024 * 1024 * 1024
    max_input_bytes: int = 20_000_000
    max_output_bytes: int = 64 * 1024 * 1024
    max_pages: int = 256
    archive_max_file_bytes: int = 128 * 1024 * 1024
    archive_max_total_bytes: int = 512 * 1024 * 1024
    archive_max_member_count: int = 10_000
    temporary_directory: str = "/tmp"

    @classmethod
    def from_environment(cls) -> "ParserWorkerSettings":
        return cls(
            max_concurrent=_environment_int("PARSER_MAX_CONCURRENT", cls.max_concurrent),
            timeout_seconds=_environment_int("PARSER_TIMEOUT_SECONDS", cls.timeout_seconds),
            process_cpu_seconds=_environment_int("PARSER_PROCESS_CPU_SECONDS", cls.process_cpu_seconds),
            process_memory_bytes=_environment_int("PARSER_PROCESS_MEMORY_BYTES", cls.process_memory_bytes),
            max_input_bytes=_environment_int("PARSER_MAX_INPUT_BYTES", cls.max_input_bytes),
            max_output_bytes=_environment_int("PARSER_MAX_OUTPUT_BYTES", cls.max_output_bytes),
            max_pages=_environment_int("PARSER_MAX_PAGES", cls.max_pages),
            archive_max_file_bytes=_environment_int("PARSER_ARCHIVE_MAX_FILE_BYTES", cls.archive_max_file_bytes),
            archive_max_total_bytes=_environment_int("PARSER_ARCHIVE_MAX_TOTAL_BYTES", cls.archive_max_total_bytes),
            archive_max_member_count=_environment_int("PARSER_ARCHIVE_MAX_MEMBER_COUNT", cls.archive_max_member_count),
            temporary_directory=os.environ.get("PARSER_TEMPORARY_DIRECTORY", cls.temporary_directory),
        )


class UploadSizeExceededError(Exception):
    pass


def _process_upload(
    source: BinaryIO,
    filename: str,
    content_type: str,
    pages: list[int] | None,
    settings: ParserWorkerSettings,
    runner: Callable[..., str | list[dict]],
) -> str | list[dict]:
    with tempfile.TemporaryDirectory(prefix="parser-", dir=settings.temporary_directory) as directory:
        input_path = Path(directory) / "input"
        source.seek(0)
        total_bytes = 0
        with input_path.open("wb") as destination:
            while chunk := source.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > settings.max_input_bytes:
                    raise UploadSizeExceededError()
                destination.write(chunk)

        request = ParserProcessRequest(
            input_path=str(input_path),
            filename=filename,
            content_type=content_type,
            pages=pages,
            max_input_bytes=settings.max_input_bytes,
            max_output_bytes=settings.max_output_bytes,
            max_pages=settings.max_pages,
            archive_max_file_bytes=settings.archive_max_file_bytes,
            archive_max_total_bytes=settings.archive_max_total_bytes,
            archive_max_member_count=settings.archive_max_member_count,
        )
        return runner(
            request=request,
            timeout_seconds=settings.timeout_seconds,
            cpu_seconds=settings.process_cpu_seconds,
            memory_bytes=settings.process_memory_bytes,
        )


def create_parser_app(
    settings: ParserWorkerSettings | None = None,
    runner: Callable[..., str | list[dict]] = run_isolated,
) -> FastAPI:
    settings = settings or ParserWorkerSettings.from_environment()
    conversion_semaphore = asyncio.Semaphore(value=settings.max_concurrent)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.post("/v1/parse")
    async def parse(file: UploadFile = File(...), pages: str | None = Form(default=None)) -> JSONResponse:
        try:
            parsed_pages = json.loads(pages) if pages is not None else None
            if parsed_pages is not None and (
                not isinstance(parsed_pages, list)
                or len(parsed_pages) > settings.max_pages
                or any(not isinstance(page, int) or isinstance(page, bool) or page < 0 for page in parsed_pages)
            ):
                raise ValueError()
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=422, detail="Invalid page selection") from e

        async with conversion_semaphore:
            task = asyncio.create_task(
                asyncio.to_thread(
                    _process_upload,
                    file.file,
                    Path(file.filename or "document").name,
                    file.content_type or "application/octet-stream",
                    parsed_pages,
                    settings,
                    runner,
                )
            )
            try:
                content = await asyncio.shield(task)
            except asyncio.CancelledError:
                try:
                    await task
                except Exception:
                    pass
                raise
            except UploadSizeExceededError as e:
                raise HTTPException(status_code=413, detail="Document exceeds the input-size limit") from e
            except TimeoutError as e:
                raise HTTPException(status_code=504, detail="Document parsing timed out") from e
            except ValueError as e:
                raise HTTPException(status_code=422, detail="Document parsing failed") from e
            except Exception as e:
                logger.exception("Isolated parser worker failed")
                raise HTTPException(status_code=500, detail="Parser worker failed") from e

        return JSONResponse({"content": content})

    return app


app = create_parser_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("PARSER_HOST", "127.0.0.1"),
        port=_environment_int("PARSER_PORT", 8001),
    )
