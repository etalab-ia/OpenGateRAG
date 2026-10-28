from sqlalchemy import select

from opengaterag.api.domain.user.entities import User
from opengaterag.api.infrastructure.postgres import PostgresUserRepository
from opengaterag.api.infrastructure.postgres.models import User as UserTable


class TestGetOrCreateUser:
    async def test_should_create_missing_user_with_given_storage_limit(self, db_session):
        # Arrange
        repository = PostgresUserRepository(postgres_session=db_session)

        # Act
        user = await repository.get_or_create_user(user_id=42, storage_limit=1_000)

        # Assert
        assert isinstance(user, User)
        assert user.id == 42
        assert user.storage_limit == 1_000
        assert user.create_public_collection is False
        stored = await db_session.scalar(select(UserTable).where(UserTable.id == 42))
        assert stored.storage_limit == 1_000

    async def test_should_return_existing_user_without_overwriting_it(self, db_session):
        # Arrange
        db_session.add(UserTable(id=42, storage_limit=None, create_public_collection=True))
        await db_session.flush()
        repository = PostgresUserRepository(postgres_session=db_session)

        # Act
        user = await repository.get_or_create_user(user_id=42, storage_limit=1_000)

        # Assert
        assert user.storage_limit is None
        assert user.create_public_collection is True
