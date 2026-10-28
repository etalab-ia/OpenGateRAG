from collections.abc import AsyncGenerator
import os

import asyncpg
import pytest_asyncio
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from opengaterag.api.infrastructure.postgres.models import Base

TEST_POSTGRES_URL = os.getenv("TEST_POSTGRES_URL", "postgresql+asyncpg://postgres:changeme@localhost:5432/opengaterag_test")


@pytest_asyncio.fixture(scope="session")
async def test_postgres_engine() -> AsyncGenerator[AsyncEngine]:
    url = make_url(TEST_POSTGRES_URL)
    connection = await asyncpg.connect(url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False))
    try:
        await connection.execute(f'CREATE DATABASE "{url.database}"')
    except asyncpg.exceptions.DuplicateDatabaseError:
        pass
    finally:
        await connection.close()

    engine = create_async_engine(url=url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_postgres_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Every test runs inside a transaction rolled back at teardown. A commit from the code under test only releases a savepoint."""
    async with test_postgres_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
