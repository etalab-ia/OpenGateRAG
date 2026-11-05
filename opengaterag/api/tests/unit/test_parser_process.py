import json
import os
from pathlib import Path
import resource
import time

import pymupdf
import pytest

from opengaterag.api.helpers._parser_process import ParserProcessRequest, run_isolated
from opengaterag.api.tests.document_fixtures import DOCX_MIME, build_docx


def make_request(path: Path, content_type: str = "text/plain") -> ParserProcessRequest:
    return ParserProcessRequest(
        input_path=str(path),
        filename=path.name,
        content_type=content_type,
        pages=None,
        max_input_bytes=20_000_000,
        max_output_bytes=1024 * 1024,
        max_pages=10,
        archive_max_file_bytes=1024 * 1024,
        archive_max_total_bytes=2 * 1024 * 1024,
        archive_max_member_count=100,
    )


def _environment_and_limits_probe(connection, request: ParserProcessRequest) -> None:
    connection.send(
        {
            "ok": True,
            "content": json.dumps(
                {
                    "environment": sorted(os.environ),
                    "cpu": resource.getrlimit(resource.RLIMIT_CPU),
                    "memory": resource.getrlimit(resource.RLIMIT_AS),
                }
            ),
        }
    )


def _hang(connection, request: ParserProcessRequest) -> None:
    Path(request.input_path).write_text(str(os.getpid()))
    time.sleep(60)


def _crash(connection, request: ParserProcessRequest) -> None:
    os._exit(23)


def test_real_parser_runs_in_a_subprocess(tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("hello isolated parser")

    parsed = run_isolated(make_request(source), timeout_seconds=30, cpu_seconds=30, memory_bytes=1024 * 1024 * 1024)

    assert parsed == [{"text": "hello isolated parser", "metadata": {}}]


def test_docling_runs_under_process_resource_limits(tmp_path):
    source = tmp_path / "sample.docx"
    source.write_bytes(build_docx(source))

    parsed = run_isolated(make_request(source, DOCX_MIME), timeout_seconds=30, cpu_seconds=30, memory_bytes=1024 * 1024 * 1024)

    assert "DOCX milestone" in parsed[0]["text"]
    assert parsed[0]["metadata"]["heading"] == "DOCX milestone"
    assert parsed[0]["metadata"]["parser_name"] == "docling"


def test_pdf_runs_under_process_resource_limits(tmp_path):
    source = tmp_path / "sample.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "PDF isolated parser marker")
        source.write_bytes(document.tobytes())

    parsed = run_isolated(make_request(source, "application/pdf"), timeout_seconds=30, cpu_seconds=30, memory_bytes=1024 * 1024 * 1024)

    assert isinstance(parsed, list)
    assert "PDF isolated parser marker" in parsed[0]["text"]


def test_child_environment_and_resource_limits_are_applied(tmp_path, monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "must-not-reach-the-parser")
    monkeypatch.setenv("OPENGATELLM_API_KEY", "must-not-reach-the-parser")

    parsed = run_isolated(
        make_request(tmp_path / "notes.txt"),
        timeout_seconds=10,
        cpu_seconds=17,
        memory_bytes=512 * 1024 * 1024,
        entrypoint=_environment_and_limits_probe,
    )
    result = json.loads(parsed)

    assert "POSTGRES_PASSWORD" not in result["environment"]
    assert "OPENGATELLM_API_KEY" not in result["environment"]
    assert "PATH" in result["environment"]
    assert result["cpu"] == [17, 17]
    assert result["memory"] == [512 * 1024 * 1024, 512 * 1024 * 1024]


def test_timeout_terminates_the_child_process(tmp_path):
    source = tmp_path / "pid.txt"

    with pytest.raises(TimeoutError, match="timed out"):
        run_isolated(make_request(source), timeout_seconds=2, cpu_seconds=30, memory_bytes=512 * 1024 * 1024, entrypoint=_hang)

    child_pid = int(source.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)


def test_child_crash_is_reported(tmp_path):
    with pytest.raises(RuntimeError, match="without a result"):
        run_isolated(make_request(tmp_path / "notes.txt"), timeout_seconds=10, cpu_seconds=30, memory_bytes=512 * 1024 * 1024, entrypoint=_crash)
