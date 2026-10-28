from abc import ABC, abstractmethod

from opengaterag.api.domain.collection.entities import Collection, CollectionVisibility


class CollectionRepository(ABC):
    @abstractmethod
    async def create_collection(self, user_id: int, name: str, description: str | None, visibility: CollectionVisibility) -> Collection:
        pass
