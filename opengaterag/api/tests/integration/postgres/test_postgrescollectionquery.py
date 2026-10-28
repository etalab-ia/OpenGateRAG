from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView
from opengaterag.api.infrastructure.postgres import PostgresCollectionQuery
from opengaterag.api.infrastructure.postgres.models import Collection as CollectionTable
from opengaterag.api.infrastructure.postgres.models import Document as DocumentTable


async def _add_collection(db_session, documents: int) -> int:
    collection = CollectionTable(user_id=42, name="my-collection", description=None, visibility=CollectionVisibility.PRIVATE)
    db_session.add(collection)
    await db_session.flush()
    db_session.add_all(DocumentTable(collection_id=collection.id, name=f"document-{index}.pdf") for index in range(documents))
    await db_session.flush()

    return collection.id


class TestGetCollection:
    async def test_should_return_collection_with_its_own_document_count(self, db_session):
        # Arrange
        collection_id = await _add_collection(db_session, documents=2)
        await _add_collection(db_session, documents=3)
        query = PostgresCollectionQuery(postgres_session=db_session)

        # Act
        collection = await query.get_collection(collection_id=collection_id)

        # Assert
        assert isinstance(collection, CollectionView)
        assert collection.id == collection_id
        assert collection.documents == 2

    async def test_should_return_collection_not_found_error_for_unknown_id(self, db_session):
        # Arrange
        query = PostgresCollectionQuery(postgres_session=db_session)

        # Act
        result = await query.get_collection(collection_id=999_999)

        # Assert
        assert result == CollectionNotFoundError(collection_id=999_999)
