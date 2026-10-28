from datetime import UTC, datetime

import pytest

from opengaterag.api.domain.collection.entities import Collection, CollectionVisibility

OWNER_ID = 1
OTHER_USER_ID = 2
NOW = datetime(2030, 1, 1, tzinfo=UTC)


def _collection(visibility: CollectionVisibility) -> Collection:
    return Collection(id=7, user_id=OWNER_ID, name="my-collection", description=None, visibility=visibility, created=NOW, updated=NOW)


class TestIsReadableBy:
    @pytest.mark.parametrize(
        "visibility,user_id,expected",
        [
            (CollectionVisibility.PRIVATE, OWNER_ID, True),
            (CollectionVisibility.PUBLIC, OWNER_ID, True),
            (CollectionVisibility.PUBLIC, OTHER_USER_ID, True),
            (CollectionVisibility.PRIVATE, OTHER_USER_ID, False),
        ],
    )
    def test_should_be_readable_by_owner_or_anyone_when_public(self, visibility, user_id, expected):
        # Act
        is_readable = _collection(visibility).is_readable_by(user_id=user_id)

        # Assert
        assert is_readable is expected
