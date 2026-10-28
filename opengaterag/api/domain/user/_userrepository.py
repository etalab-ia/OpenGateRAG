from abc import ABC, abstractmethod

from opengaterag.api.domain.user.entities import User


class UserRepository(ABC):
    @abstractmethod
    async def get_or_create_user(self, user_id: int, storage_limit: int | None) -> User:
        pass
