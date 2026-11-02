from abc import ABC, abstractmethod

from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView


class CollectionQuery(ABC):
    @abstractmethod
    async def get_collection(self, collection_id: int) -> CollectionView | CollectionNotFoundError:
        pass
