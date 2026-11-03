from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from opengaterag.api.domain.collection import CollectionQuery
from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView
from opengaterag.api.domain.document import DocumentRepository
from opengaterag.api.domain.document.entities import Document
from opengaterag.api.domain.document.errors import DocumentNotFoundError
from opengaterag.api.use_cases.documents import GetOneDocumentCommand, GetOneDocumentUseCase, GetOneDocumentUseCaseSuccess

OWNER_ID = 1
OTHER_USER_ID = 2
COLLECTION_ID = 7
DOCUMENT_ID = 42
NOW = datetime(2030, 1, 1, tzinfo=UTC)

DOCUMENT = Document(id=DOCUMENT_ID, collection_id=COLLECTION_ID, name="document.pdf", created=NOW)


def _collection_view(visibility: CollectionVisibility) -> CollectionView:
    return CollectionView(
        id=COLLECTION_ID,
        user_id=OWNER_ID,
        name="my-collection",
        description=None,
        visibility=visibility,
        created=NOW,
        updated=NOW,
        documents=1,
    )


@pytest.fixture
def mock_document_repository():
    return create_autospec(DocumentRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_collection_query():
    return create_autospec(CollectionQuery, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_document_repository, mock_collection_query):
    return GetOneDocumentUseCase(document_repository=mock_document_repository, collection_query=mock_collection_query)


class TestGetOneDocumentUseCase:
    async def test_should_return_document_of_readable_collection(self, use_case, mock_document_repository, mock_collection_query):
        # Arrange
        mock_document_repository.get_document.return_value = DOCUMENT
        mock_collection_query.get_collection.return_value = _collection_view(CollectionVisibility.PRIVATE)

        # Act
        result = await use_case.execute(GetOneDocumentCommand(user_id=OWNER_ID, document_id=DOCUMENT_ID))

        # Assert
        assert result == GetOneDocumentUseCaseSuccess(document=DOCUMENT)
        mock_document_repository.get_document.assert_awaited_once_with(document_id=DOCUMENT_ID)
        mock_collection_query.get_collection.assert_awaited_once_with(collection_id=COLLECTION_ID)

    async def test_should_return_document_not_found_error_when_collection_is_not_readable(self, use_case, mock_document_repository, mock_collection_query):  # fmt: off
        # Arrange
        mock_document_repository.get_document.return_value = DOCUMENT
        mock_collection_query.get_collection.return_value = _collection_view(CollectionVisibility.PRIVATE)

        # Act
        result = await use_case.execute(GetOneDocumentCommand(user_id=OTHER_USER_ID, document_id=DOCUMENT_ID))

        # Assert
        assert result == DocumentNotFoundError()

    async def test_should_return_document_not_found_error_when_collection_does_not_exist(self, use_case, mock_document_repository, mock_collection_query):  # fmt: off
        # Arrange
        mock_document_repository.get_document.return_value = DOCUMENT
        mock_collection_query.get_collection.return_value = CollectionNotFoundError()

        # Act
        result = await use_case.execute(GetOneDocumentCommand(user_id=OWNER_ID, document_id=DOCUMENT_ID))

        # Assert
        assert result == DocumentNotFoundError()

    async def test_should_return_document_not_found_error_when_document_does_not_exist(self, use_case, mock_document_repository, mock_collection_query):  # fmt: off
        # Arrange
        mock_document_repository.get_document.return_value = DocumentNotFoundError()

        # Act
        result = await use_case.execute(GetOneDocumentCommand(user_id=OWNER_ID, document_id=DOCUMENT_ID))

        # Assert
        assert result == DocumentNotFoundError()
        mock_collection_query.get_collection.assert_not_awaited()
