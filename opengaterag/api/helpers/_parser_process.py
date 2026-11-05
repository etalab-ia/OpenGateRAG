import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import multiprocessing
import os
from pathlib import Path
import resource
from typing import Any


@dataclass(frozen=True)
class ParserProcessRequest:
    input_path: str
    filename: str
    content_type: str
    pages: list[int] | None
    max_input_bytes: int
    max_output_bytes: int
    max_pages: int
    archive_max_file_bytes: int
    archive_max_total_bytes: int
    archive_max_member_count: int


def _parse_document(connection: Any, request: ParserProcessRequest) -> None:
    from fastapi import UploadFile
    from starlette.datastructures import Headers

    from opengaterag.api.helpers._parsermanager import ParserArchiveLimits, ParserManager

    parser = ParserManager(
        max_concurrent=1,
        max_input_bytes=request.max_input_bytes,
        max_output_bytes=request.max_output_bytes,
        max_pages=request.max_pages,
        archive_limits=ParserArchiveLimits(
            max_file_bytes=request.archive_max_file_bytes,
            max_total_bytes=request.archive_max_total_bytes,
            max_member_count=request.archive_max_member_count,
        ),
    )
    input_path = os.path.realpath(request.input_path, strict=True)
    with open(input_path, "rb") as source:
        upload = UploadFile(filename=request.filename, file=source, headers=Headers({"content-type": request.content_type}))
        content = asyncio.run(parser.parse(file=upload, pages=request.pages))
    connection.send({"ok": True, "content": content})


def _prepare_child(request: ParserProcessRequest, cpu_seconds: int, memory_bytes: int) -> None:
    temporary_directory = str(Path(request.input_path).parent)
    os.environ.clear()
    os.environ.update(
        {
            "HOME": temporary_directory,
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": os.defpath,
            "TMPDIR": temporary_directory,
        }
    )
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))


def _child_bootstrap(
    entrypoint: Callable[[Any, ParserProcessRequest], None],
    connection: Any,
    request: ParserProcessRequest,
    cpu_seconds: int,
    memory_bytes: int,
) -> None:
    try:
        _prepare_child(request=request, cpu_seconds=cpu_seconds, memory_bytes=memory_bytes)
        entrypoint(connection, request)
    except Exception as e:
        try:
            connection.send({"ok": False, "error": type(e).__name__})
        except (BrokenPipeError, EOFError, OSError):
            pass
    finally:
        connection.close()


def run_isolated(
    request: ParserProcessRequest,
    timeout_seconds: int,
    cpu_seconds: int,
    memory_bytes: int,
    entrypoint: Callable[[Any, ParserProcessRequest], None] = _parse_document,
) -> str | list[dict]:
    context = multiprocessing.get_context("spawn")
    receive_connection, send_connection = context.Pipe(duplex=False)
    process = context.Process(
        target=_child_bootstrap,
        args=(entrypoint, send_connection, request, cpu_seconds, memory_bytes),
    )

    started = False
    try:
        process.start()
        started = True
        send_connection.close()
        if not receive_connection.poll(timeout_seconds):
            raise TimeoutError("Isolated document parsing timed out")
        try:
            outcome = receive_connection.recv()
        except EOFError as e:
            raise RuntimeError("Isolated document parser exited without a result") from e

        if not isinstance(outcome, dict) or "ok" not in outcome:
            raise RuntimeError("Isolated document parser returned an invalid result")
        if not outcome["ok"]:
            error_type = outcome.get("error", "unknown error")
            raise ValueError(f"Isolated document parsing failed: {error_type}")
        return outcome["content"]
    finally:
        if started:
            process.join(timeout=0.1)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
        receive_connection.close()
        if not send_connection.closed:
            send_connection.close()
