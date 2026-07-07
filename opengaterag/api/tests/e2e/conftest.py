import asyncio
from collections.abc import Generator, Mapping
import os
from typing import Any

from elasticsearch import AsyncElasticsearch
from fastapi.testclient import TestClient
import httpx
import pytest

from opengaterag.api.main import app
from opengaterag.api.utils.configuration import configuration


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


def _validate_opengatellm_api_key(env_var: str, role: str) -> str:
    api_key = os.environ.get(env_var)
    if not api_key:
        raise ValueError(f"{env_var} is not set to run e2e tests.")
    with httpx.Client() as httpx_client:
        response = httpx_client.get(
            url=f"{configuration.dependencies.opengatellm.url}/v1/me/info",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        try:
            response.raise_for_status()
        except Exception:
            raise ValueError(f"Failed to reach OpenGateLLM API as {role}: {response.text}")
    return api_key


@pytest.fixture(scope="session")
def setup_elasticsearch_index() -> None:
    """Delete Elasticsearch index before running integration tests."""

    async def _delete_index() -> None:
        kwargs = configuration.dependencies.elasticsearch.model_dump()
        index_name = kwargs.pop("index_name")
        kwargs.pop("index_language")
        kwargs.pop("number_of_shards")
        kwargs.pop("number_of_replicas")
        kwargs.pop("refresh_interval")
        client = AsyncElasticsearch(**kwargs)
        try:
            if await client.indices.exists(index=index_name):
                await client.indices.delete(index=index_name)
        finally:
            await client.close()

    asyncio.run(_delete_index())


@pytest.fixture(scope="session")
def test_client(setup_elasticsearch_index) -> Generator[TestClient, None, None]:
    """Single TestClient for the session to keep one event loop and one app lifespan."""
    with TestClient(app=app) as client:
        yield client


@pytest.fixture(scope="session")
def user_client(test_client: TestClient) -> AuthenticatedTestClient:
    """Test client authenticated as a regular user."""
    api_key = _validate_opengatellm_api_key("OPENGATELLM_USER_API_KEY", "user")
    return AuthenticatedTestClient(client=test_client, api_key=api_key)


@pytest.fixture(scope="session")
def admin_client(test_client: TestClient) -> AuthenticatedTestClient:
    """Test client authenticated as an admin user."""
    api_key = _validate_opengatellm_api_key("OPENGATELLM_ADMIN_API_KEY", "admin")
    return AuthenticatedTestClient(client=test_client, api_key=api_key)
