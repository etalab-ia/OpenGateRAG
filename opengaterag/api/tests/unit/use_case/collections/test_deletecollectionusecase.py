from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from opengaterag.api.domain.collection import CollectionQuery, CollectionRepository
from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView
from opengaterag.api.use_cases.collections import DeleteCollectionCommand, DeleteCollectionUseCase, DeleteCollectionUseCaseSuccess

OWNER_ID = 1
OTHER_USER_ID = 2
COLLECTION_ID = 7
NOW = datetime(2030, 1, 1, tzinfo=UTC)


def _stored_collection_view(visibility: CollectionVisibility = CollectionVisibility.PRIVATE) -> CollectionView:
    return CollectionView(
        id=COLLECTION_ID,
        user_id=OWNER_ID,
        name="my-collection",
        description=None,
        visibility=visibility,
        created=NOW,
        updated=NOW,
        documents=3,
    )


def _command(user_id: int = OWNER_ID) -> DeleteCollectionCommand:
    return DeleteCollectionCommand(user_id=user_id, collection_id=COLLECTION_ID)


@pytest.fixture
def mock_collection_repository():
    return create_autospec(CollectionRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_collection_query():
    return create_autospec(CollectionQuery, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_collection_repository, mock_collection_query):
    return DeleteCollectionUseCase(collection_repository=mock_collection_repository, collection_query=mock_collection_query)


class TestDeleteCollectionUseCase:
    async def test_should_delete_own_collection(self, use_case, mock_collection_repository, mock_collection_query):
        # Arrange
        mock_collection_query.get_collection.return_value = _stored_collection_view()
        mock_collection_repository.delete_collection.return_value = None

        # Act
        result = await use_case.execute(_command())

        # Assert
        assert result == DeleteCollectionUseCaseSuccess()
        mock_collection_repository.delete_collection.assert_awaited_once_with(collection_id=COLLECTION_ID)

    async def test_should_return_collection_not_found_error_when_collection_does_not_exist(
        self, use_case, mock_collection_repository, mock_collection_query
    ):
        # Arrange
        mock_collection_query.get_collection.return_value = CollectionNotFoundError()

        # Act
        result = await use_case.execute(_command())

        # Assert
        assert result == CollectionNotFoundError()
        mock_collection_repository.delete_collection.assert_not_awaited()

    @pytest.mark.parametrize("visibility", [CollectionVisibility.PRIVATE, CollectionVisibility.PUBLIC])
    async def test_should_return_collection_not_found_error_when_user_is_not_owner(
        self, use_case, mock_collection_repository, mock_collection_query, visibility
    ):
        # Arrange
        mock_collection_query.get_collection.return_value = _stored_collection_view(visibility)

        # Act
        result = await use_case.execute(_command(user_id=OTHER_USER_ID))

        # Assert
        assert result == CollectionNotFoundError()
        mock_collection_repository.delete_collection.assert_not_awaited()
