from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from opengaterag.api.dependencies import get_authenticated_user_query
from opengaterag.api.domain.user import AuthenticatedUserQuery
from opengaterag.api.domain.user.errors import UserNotAuthenticatedError
from opengaterag.api.domain.user.views import AuthenticatedUserView
from opengaterag.api.infrastructure.fastapi.endpoints.exceptions import InvalidAPIKeyHTTPException

http_bearer = HTTPBearer()


class AccessController:
    async def __call__(
        self,
        api_key: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
        authenticated_user_query: AuthenticatedUserQuery = Depends(get_authenticated_user_query),
    ) -> AuthenticatedUserView:
        result = await authenticated_user_query.get_user_by_api_key(api_key=api_key.credentials)

        match result:
            case UserNotAuthenticatedError():
                raise InvalidAPIKeyHTTPException()
            case AuthenticatedUserView() as user:
                return user
