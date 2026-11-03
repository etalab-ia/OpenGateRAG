from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.document.entities import Document
from opengaterag.api.domain.document.errors import DocumentNotFoundError
from opengaterag.api.infrastructure.postgres import PostgresDocumentRepository
from opengaterag.api.infrastructure.postgres.models import Collection as CollectionTable
from opengaterag.api.infrastructure.postgres.models import Document as DocumentTable


class TestGetDocument:
    async def test_should_read_document(self, db_session):
        # Arrange
        repository = PostgresDocumentRepository(postgres_session=db_session)
        collection = CollectionTable(user_id=42, name="my-collection", description=None, visibility=CollectionVisibility.PRIVATE)
        db_session.add(collection)
        await db_session.flush()
        stored = DocumentTable(collection_id=collection.id, name="document.pdf")
        db_session.add(stored)
        await db_session.flush()

        # Act
        document = await repository.get_document(document_id=stored.id)

        # Assert
        assert isinstance(document, Document)
        assert document.collection_id == collection.id
        assert document.name == "document.pdf"
        assert document.created.tzinfo is not None

    async def test_should_return_document_not_found_error_when_document_does_not_exist(self, db_session):
        # Arrange
        repository = PostgresDocumentRepository(postgres_session=db_session)

        # Act
        result = await repository.get_document(document_id=999_999)

        # Assert
        assert result == DocumentNotFoundError()
