from abc import ABC, abstractmethod

from opengaterag.api.domain.collection.entities import Collection, CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError


class CollectionRepository(ABC):
    @abstractmethod
    async def create_collection(self, user_id: int, name: str, description: str | None, visibility: CollectionVisibility) -> Collection:
        pass

    @abstractmethod
    async def update_collection(self, collection_id: int, name: str, description: str | None) -> Collection | CollectionNotFoundError:
        pass

    @abstractmethod
    async def delete_collection(self, collection_id: int) -> None | CollectionNotFoundError:
        pass
