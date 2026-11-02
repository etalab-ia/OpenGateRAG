from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from opengaterag.api.domain.collection import CollectionQuery
from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView
from opengaterag.api.use_cases.collections import GetOneCollectionCommand, GetOneCollectionUseCase, GetOneCollectionUseCaseSuccess

OWNER_ID = 1
OTHER_USER_ID = 2
COLLECTION_ID = 7
NOW = datetime(2030, 1, 1, tzinfo=UTC)


def _collection_view(visibility: CollectionVisibility) -> CollectionView:
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


@pytest.fixture
def mock_collection_query():
    return create_autospec(CollectionQuery, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_collection_query):
    return GetOneCollectionUseCase(collection_query=mock_collection_query)


class TestGetOneCollectionUseCase:
    async def test_should_return_readable_collection(self, use_case, mock_collection_query):
        # Arrange
        mock_collection_query.get_collection.return_value = _collection_view(CollectionVisibility.PRIVATE)

        # Act
        result = await use_case.execute(GetOneCollectionCommand(user_id=OWNER_ID, collection_id=COLLECTION_ID))

        # Assert
        assert result == GetOneCollectionUseCaseSuccess(collection=_collection_view(CollectionVisibility.PRIVATE))
        mock_collection_query.get_collection.assert_awaited_once_with(collection_id=COLLECTION_ID)

    async def test_should_return_collection_not_found_error_when_collection_is_not_readable(self, use_case, mock_collection_query):
        # Arrange
        mock_collection_query.get_collection.return_value = _collection_view(CollectionVisibility.PRIVATE)

        # Act
        result = await use_case.execute(GetOneCollectionCommand(user_id=OTHER_USER_ID, collection_id=COLLECTION_ID))

        # Assert
        assert result == CollectionNotFoundError(collection_id=COLLECTION_ID)

    async def test_should_return_collection_not_found_error_when_collection_does_not_exist(self, use_case, mock_collection_query):
        # Arrange
        mock_collection_query.get_collection.return_value = CollectionNotFoundError(collection_id=COLLECTION_ID)

        # Act
        result = await use_case.execute(GetOneCollectionCommand(user_id=OWNER_ID, collection_id=COLLECTION_ID))

        # Assert
        assert result == CollectionNotFoundError(collection_id=COLLECTION_ID)
