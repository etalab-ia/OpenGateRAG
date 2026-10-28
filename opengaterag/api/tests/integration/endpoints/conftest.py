from collections.abc import AsyncGenerator
from unittest.mock import create_autospec

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from opengaterag.api.app import create_app
from opengaterag.api.dependencies import get_authenticated_user_query, get_postgres_session
from opengaterag.api.domain.user import AuthenticatedUserQuery
from opengaterag.api.domain.user.views import AuthenticatedUserView
from opengaterag.api.infrastructure.configuration import Configuration, Dependencies, OpengateLLMDependency, Settings, get_configuration

AUTHENTICATED_USER_ID = 1
API_KEY = "sk-test"


@pytest.fixture(scope="session")
def test_configuration() -> Configuration:
    return Configuration.model_construct(
        dependencies=Dependencies.model_construct(opengatellm=OpengateLLMDependency.model_construct(url="http://opengatellm.test"), sentry=None),
        settings=Settings(monitoring_prometheus_enabled=False),
    )


@pytest.fixture
def app(test_configuration: Configuration, db_session: AsyncSession) -> FastAPI:
    app = create_app(configuration=test_configuration, skip_lifespan=True)
    app.dependency_overrides[get_configuration] = lambda: test_configuration
    app.dependency_overrides[get_postgres_session] = lambda: db_session

    return app


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_authenticated_user_query(app: FastAPI):
    mock_authenticated_user_query = create_autospec(AuthenticatedUserQuery, instance=True, spec_set=True)
    mock_authenticated_user_query.get_user_by_api_key.return_value = AuthenticatedUserView(id=AUTHENTICATED_USER_ID)
    app.dependency_overrides[get_authenticated_user_query] = lambda: mock_authenticated_user_query

    return mock_authenticated_user_query
