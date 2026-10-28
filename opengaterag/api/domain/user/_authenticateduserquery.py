from abc import ABC, abstractmethod

from opengaterag.api.domain.user.errors import UserNotAuthenticatedError
from opengaterag.api.domain.user.views import AuthenticatedUserView


class AuthenticatedUserQuery(ABC):
    @abstractmethod
    async def get_user_by_api_key(self, api_key: str) -> AuthenticatedUserView | UserNotAuthenticatedError:
        pass
