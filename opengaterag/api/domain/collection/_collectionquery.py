from abc import ABC, abstractmethod

from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView


class CollectionQuery(ABC):
    @abstractmethod
    async def get_collection(self, collection_id: int) -> CollectionView | CollectionNotFoundError:
        pass

    @abstractmethod
    async def get_readable_collections(self, user_id: int, offset: int, limit: int) -> tuple[list[CollectionView], int]:
        """Return one page of the collections the user can read, and the total number of those collections."""
        pass
