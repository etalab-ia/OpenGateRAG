from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient
import yaml

from opengaterag.api.parser_worker import ParserWorkerSettings, create_parser_app


def make_client(tmp_path, runner=None, max_input_bytes=20_000_000) -> tuple[TestClient, Mock]:
    parser_runner = runner or Mock(return_value="parsed text")
    settings = ParserWorkerSettings(temporary_directory=str(tmp_path), max_input_bytes=max_input_bytes)
    return TestClient(create_parser_app(settings=settings, runner=parser_runner)), parser_runner


def test_worker_health_does_not_need_application_configuration(tmp_path):
    client, _ = make_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_worker_removes_temporary_files_after_success(tmp_path):
    client, runner = make_client(tmp_path)

    response = client.post("/v1/parse", files={"file": ("notes.txt", b"text", "text/plain")})

    assert response.status_code == 200
    assert response.json() == {"content": "parsed text"}
    request = runner.call_args.kwargs["request"]
    assert not Path(request.input_path).exists()
    assert list(tmp_path.iterdir()) == []


def test_worker_rejects_oversized_input_before_running_parser(tmp_path):
    client, runner = make_client(tmp_path, max_input_bytes=4)

    response = client.post("/v1/parse", files={"file": ("notes.txt", b"12345", "text/plain")})

    assert response.status_code == 413
    runner.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def test_worker_timeout_is_repeatable_and_cleans_up(tmp_path):
    runner = Mock(side_effect=TimeoutError("expired"))
    client, _ = make_client(tmp_path, runner=runner)

    responses = [client.post("/v1/parse", files={"file": ("notes.txt", b"text", "text/plain")}) for _ in range(2)]

    assert [response.status_code for response in responses] == [504, 504]
    assert runner.call_count == 2
    assert list(tmp_path.iterdir()) == []


def test_worker_rejects_invalid_page_selection(tmp_path):
    client, runner = make_client(tmp_path)

    response = client.post(
        "/v1/parse",
        data={"pages": "[true]"},
        files={"file": ("notes.txt", b"text", "text/plain")},
    )

    assert response.status_code == 422
    runner.assert_not_called()


def test_compose_parser_is_isolated_and_resource_bounded():
    repository_root = Path(__file__).resolve().parents[4]
    compose = yaml.safe_load((repository_root / "compose.example.yml").read_text())
    parser = compose["services"]["parser"]

    assert compose["networks"]["parser_internal"]["internal"] is True
    assert parser["networks"] == ["parser_internal"]
    assert "ports" not in parser
    assert "env_file" not in parser
    assert "volumes" not in parser
    assert parser["read_only"] is True
    assert parser["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in parser["security_opt"]
    assert parser["cpus"]
    assert parser["mem_limit"]
    assert parser["pids_limit"]
    assert any("noexec" in mount and "size=" in mount for mount in parser["tmpfs"])
    assert compose["services"]["rag"]["depends_on"]["parser"]["condition"] == "service_healthy"

    environment = parser["environment"]
    assert not any(value.startswith(("POSTGRES_", "OPENGATELLM_", "ELASTICSEARCH_")) for value in environment)
    assert "USER opengaterag" in (repository_root / "opengaterag/api/Dockerfile").read_text()
