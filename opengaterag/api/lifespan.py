from contextlib import asynccontextmanager

from fastapi import FastAPI
import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from opengaterag.api.infrastructure.configuration import Configuration, get_configuration
from opengaterag.api.infrastructure.context import global_context

OPENGATELLM_TIMEOUT_SECONDS = 10
OPENGATELLM_HEALTH_TIMEOUT_SECONDS = 60


@asynccontextmanager
async def lifespan(_: FastAPI):
    configuration = get_configuration()

    global_context.opengatellm_client = create_opengatellm_client(configuration)
    await check_opengatellm_health(global_context.opengatellm_client)
    global_context.postgres_engine = create_postgres_engine(configuration)
    global_context.postgres_session_factory = create_postgres_session_factory(engine=global_context.postgres_engine)

    yield

    await global_context.opengatellm_client.aclose()
    await global_context.postgres_engine.dispose()


def create_opengatellm_client(configuration: Configuration) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=configuration.dependencies.opengatellm.url, timeout=OPENGATELLM_TIMEOUT_SECONDS)


async def check_opengatellm_health(opengatellm_client: httpx.AsyncClient) -> None:
    response = await opengatellm_client.get(url="/health", timeout=OPENGATELLM_HEALTH_TIMEOUT_SECONDS)
    if response.status_code != 200:
        raise RuntimeError("OpenGateLLM is not reachable.")


def create_postgres_engine(configuration: Configuration) -> AsyncEngine:
    return create_async_engine(**configuration.dependencies.postgres.model_dump())


def create_postgres_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
