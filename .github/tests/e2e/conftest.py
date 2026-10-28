from collections.abc import Generator, Mapping
import os
from typing import Any

from fastapi.testclient import TestClient
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

# Must be set before importing the app, which interpolates the config file.
os.environ.setdefault("POSTGRES_DB", "opengaterag")

from opengaterag.api.main import app  # noqa: E402
from opengaterag.api.utils.configuration import configuration  # noqa: E402
from opengaterag.api.utils.sql import User as UserTable  # noqa: E402


class AuthenticatedTestClient:
    """Wrap a shared TestClient and inject auth headers per request."""

    def __init__(self, client: TestClient, api_key: str) -> None:
        self._client = client
        self._auth_headers = {"Authorization": f"Bearer {api_key}"}

    def _merge_headers(self, headers: Mapping[str, str] | None) -> dict[str, str]:
        merged = dict(self._auth_headers)
        if headers:
            merged.update(headers)
        return merged

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        kwargs["headers"] = self._merge_headers(kwargs.get("headers"))
        return self._client.get(url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        kwargs["headers"] = self._merge_headers(kwargs.get("headers"))
        return self._client.post(url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        kwargs["headers"] = self._merge_headers(kwargs.get("headers"))
        return self._client.patch(url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        kwargs["headers"] = self._merge_headers(kwargs.get("headers"))
        return self._client.delete(url, **kwargs)


def _validate_opengatellm_api_key(env_var: str, role: str) -> tuple[str, int]:
    api_key = os.environ.get(env_var)
    if not api_key:
        raise ValueError(f"{env_var} is not set to run e2e tests.")
    with httpx.Client() as httpx_client:
        response = httpx_client.get(
            url=f"{configuration.dependencies.opengatellm.url}/v1/me",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        try:
            response.raise_for_status()
        except Exception:
            raise ValueError(f"Failed to reach OpenGateLLM API as {role}: {response.text}")
    return api_key, response.json()["id"]


def _upsert_ogr_user(*, user_id: int, create_public_collection: bool) -> None:
    url = configuration.dependencies.postgres.url.replace("+asyncpg", "")
    engine = create_engine(url)
    try:
        with Session(engine) as session:
            statement = (
                pg_insert(UserTable)
                .values(
                    id=user_id,
                    create_public_collection=create_public_collection,
                    storage_limit=configuration.settings.storage_default_limit,
                )
                .on_conflict_do_update(
                    index_elements=[UserTable.id],
                    set_={"create_public_collection": create_public_collection},
                )
            )
            session.execute(statement)
            session.commit()
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def test_client() -> Generator[TestClient, None, None]:
    """Single TestClient for the session to keep one event loop and one app lifespan."""
    with TestClient(app=app) as client:
        yield client


@pytest.fixture(scope="session")
def user_client(test_client: TestClient) -> AuthenticatedTestClient:
    """Test client authenticated as a regular user."""
    api_key, _user_id = _validate_opengatellm_api_key("OPENGATELLM_USER_API_KEY", "user")
    return AuthenticatedTestClient(client=test_client, api_key=api_key)


@pytest.fixture(scope="session")
def admin_client(test_client: TestClient) -> AuthenticatedTestClient:
    """Test client authenticated as an admin user with OGR create_public_collection."""
    api_key, user_id = _validate_opengatellm_api_key("OPENGATELLM_ADMIN_API_KEY", "admin")
    _upsert_ogr_user(user_id=user_id, create_public_collection=True)
    return AuthenticatedTestClient(client=test_client, api_key=api_key)
