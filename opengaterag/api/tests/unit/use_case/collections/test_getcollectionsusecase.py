from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from opengaterag.api.domain.collection import CollectionQuery
from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.collection.views import CollectionView
from opengaterag.api.use_cases.collections import GetCollectionsCommand, GetCollectionsUseCase, GetCollectionsUseCaseSuccess

USER_ID = 1
NOW = datetime(2030, 1, 1, tzinfo=UTC)
COLLECTION_VIEW = CollectionView(
    id=7,
    user_id=USER_ID,
    name="my-collection",
    description=None,
    visibility=CollectionVisibility.PRIVATE,
    created=NOW,
    updated=NOW,
    documents=3,
)


@pytest.fixture
def mock_collection_query():
    return create_autospec(CollectionQuery, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_collection_query):
    return GetCollectionsUseCase(collection_query=mock_collection_query)


class TestGetCollectionsUseCase:
    async def test_should_return_page_of_readable_collections(self, use_case, mock_collection_query):
        # Arrange
        mock_collection_query.get_readable_collections.return_value = ([COLLECTION_VIEW], 12)

        # Act
        result = await use_case.execute(
            GetCollectionsCommand(user_id=USER_ID, name="my-collection", visibility=CollectionVisibility.PRIVATE, offset=5, limit=1)
        )

        # Assert
        assert result == GetCollectionsUseCaseSuccess(data=[COLLECTION_VIEW], total=12, offset=5, limit=1)
        mock_collection_query.get_readable_collections.assert_awaited_once_with(
            user_id=USER_ID, name="my-collection", visibility=CollectionVisibility.PRIVATE, offset=5, limit=1
        )
