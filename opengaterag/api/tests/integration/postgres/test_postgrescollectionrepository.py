from sqlalchemy import select

from opengaterag.api.domain.collection.entities import Collection, CollectionVisibility
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
