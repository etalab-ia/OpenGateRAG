from datetime import UTC, datetime

from sqlalchemy import select

from opengaterag.api.domain.collection.entities import Collection, CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.infrastructure.postgres import PostgresCollectionRepository
from opengaterag.api.infrastructure.postgres.models import Collection as CollectionTable


class TestCreateCollection:
    async def test_should_persist_collection_without_user_row(self, db_session):
        # Arrange
        repository = PostgresCollectionRepository(postgres_session=db_session)

        # Act
        collection = await repository.create_collection(user_id=42, name="my-collection", description=None, visibility=CollectionVisibility.PUBLIC)

        # Assert
        assert isinstance(collection, Collection)
        assert collection.user_id == 42
        assert collection.name == "my-collection"
        assert collection.description is None
        assert collection.visibility == CollectionVisibility.PUBLIC
        assert collection.created.tzinfo is not None
        stored = await db_session.scalar(select(CollectionTable).where(CollectionTable.id == collection.id))
        assert stored.user_id == 42
        assert stored.visibility == CollectionVisibility.PUBLIC


class TestUpdateCollection:
    async def test_should_replace_fields_and_bump_updated(self, db_session):
        # Arrange
        repository = PostgresCollectionRepository(postgres_session=db_session)
        long_ago = datetime(2000, 1, 1, tzinfo=UTC)
        collection = CollectionTable(user_id=42, name="old-name", description="Old.", visibility=CollectionVisibility.PRIVATE, updated=long_ago)
        db_session.add(collection)
        await db_session.flush()

        # Act
        updated = await repository.update_collection(collection_id=collection.id, name="new-name", description=None)

        # Assert
        assert isinstance(updated, Collection)
        assert updated.user_id == 42
        assert updated.name == "new-name"
        assert updated.description is None
        assert updated.visibility == CollectionVisibility.PRIVATE
        assert updated.updated > long_ago

    async def test_should_return_collection_not_found_error_when_collection_does_not_exist(self, db_session):
        # Arrange
        repository = PostgresCollectionRepository(postgres_session=db_session)

        # Act
        result = await repository.update_collection(collection_id=999_999, name="new-name", description=None)

        # Assert
        assert result == CollectionNotFoundError()
