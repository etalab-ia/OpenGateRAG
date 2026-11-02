from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView
from opengaterag.api.infrastructure.postgres import PostgresCollectionQuery
from opengaterag.api.infrastructure.postgres.models import Collection as CollectionTable
from opengaterag.api.infrastructure.postgres.models import Document as DocumentTable


async def _add_collection(db_session, documents: int = 0, user_id: int = 42, visibility: CollectionVisibility = CollectionVisibility.PRIVATE) -> int:
    collection = CollectionTable(user_id=user_id, name="my-collection", description=None, visibility=visibility)
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
        assert result == CollectionNotFoundError()


class TestGetReadableCollections:
    async def test_should_return_own_and_public_collections_but_not_private_collections_of_other_users(self, db_session):
        # Arrange
        own_private = await _add_collection(db_session, user_id=42)
        own_public = await _add_collection(db_session, user_id=42, visibility=CollectionVisibility.PUBLIC)
        other_public = await _add_collection(db_session, user_id=43, visibility=CollectionVisibility.PUBLIC)
        await _add_collection(db_session, user_id=43)
        query = PostgresCollectionQuery(postgres_session=db_session)

        # Act
        collections, total = await query.get_readable_collections(user_id=42, offset=0, limit=10)

        # Assert
        assert [collection.id for collection in collections] == [own_private, own_public, other_public]
        assert total == 3

    async def test_should_return_requested_page_with_total_of_all_pages(self, db_session):
        # Arrange
        collection_ids = [await _add_collection(db_session) for _ in range(4)]
        query = PostgresCollectionQuery(postgres_session=db_session)

        # Act
        collections, total = await query.get_readable_collections(user_id=42, offset=1, limit=2)

        # Assert
        assert [collection.id for collection in collections] == collection_ids[1:3]
        assert total == 4
