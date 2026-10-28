from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from opengaterag.api.domain.collection import CollectionRepository
from opengaterag.api.domain.collection.entities import Collection, CollectionVisibility
from opengaterag.api.domain.collection.errors import PublicCollectionNotAllowedError
from opengaterag.api.domain.collection.views import CollectionView
from opengaterag.api.domain.user import UserRepository
from opengaterag.api.domain.user.entities import User
from opengaterag.api.use_cases.collections import CreateCollectionCommand, CreateCollectionUseCase, CreateCollectionUseCaseSuccess

USER_ID = 1
COLLECTION_ID = 7
STORAGE_DEFAULT_LIMIT = 10_000_000
NOW = datetime(2030, 1, 1, tzinfo=UTC)


def _user(create_public_collection: bool = False) -> User:
    return User(id=USER_ID, storage_limit=STORAGE_DEFAULT_LIMIT, create_public_collection=create_public_collection, created=NOW, updated=NOW)


def _collection(visibility: CollectionVisibility) -> Collection:
    return Collection(id=COLLECTION_ID, user_id=USER_ID, name="my-collection", description=None, visibility=visibility, created=NOW, updated=NOW)


def _collection_view(visibility: CollectionVisibility) -> CollectionView:
    return CollectionView(**_collection(visibility).model_dump(), documents=0)


def _command(visibility: CollectionVisibility) -> CreateCollectionCommand:
    return CreateCollectionCommand(user_id=USER_ID, name="my-collection", description=None, visibility=visibility)


@pytest.fixture
def mock_user_repository():
    return create_autospec(UserRepository, instance=True, spec_set=True)


@pytest.fixture
def mock_collection_repository():
    return create_autospec(CollectionRepository, instance=True, spec_set=True)


@pytest.fixture
def use_case(mock_user_repository, mock_collection_repository):
    return CreateCollectionUseCase(
        user_repository=mock_user_repository,
        collection_repository=mock_collection_repository,
        storage_default_limit=STORAGE_DEFAULT_LIMIT,
    )


class TestCreateCollectionUseCase:
    async def test_should_create_private_collection(self, use_case, mock_user_repository, mock_collection_repository):
        # Arrange
        mock_user_repository.get_or_create_user.return_value = _user()
        mock_collection_repository.create_collection.return_value = _collection(CollectionVisibility.PRIVATE)

        # Act
        result = await use_case.execute(_command(CollectionVisibility.PRIVATE))

        # Assert
        assert result == CreateCollectionUseCaseSuccess(collection=_collection_view(CollectionVisibility.PRIVATE))
        mock_user_repository.get_or_create_user.assert_awaited_once_with(user_id=USER_ID, storage_limit=STORAGE_DEFAULT_LIMIT)
        mock_collection_repository.create_collection.assert_awaited_once_with(
            user_id=USER_ID, name="my-collection", description=None, visibility=CollectionVisibility.PRIVATE
        )

    async def test_should_create_public_collection_when_user_has_public_right(self, use_case, mock_user_repository, mock_collection_repository):
        # Arrange
        mock_user_repository.get_or_create_user.return_value = _user(create_public_collection=True)
        mock_collection_repository.create_collection.return_value = _collection(CollectionVisibility.PUBLIC)

        # Act
        result = await use_case.execute(_command(CollectionVisibility.PUBLIC))

        # Assert
        assert result == CreateCollectionUseCaseSuccess(collection=_collection_view(CollectionVisibility.PUBLIC))

    async def test_should_return_public_collection_not_allowed_error_without_creating_collection(
        self, use_case, mock_user_repository, mock_collection_repository
    ):
        # Arrange
        mock_user_repository.get_or_create_user.return_value = _user(create_public_collection=False)

        # Act
        result = await use_case.execute(_command(CollectionVisibility.PUBLIC))

        # Assert
        assert result == PublicCollectionNotAllowedError(user_id=USER_ID)
        mock_collection_repository.create_collection.assert_not_awaited()
