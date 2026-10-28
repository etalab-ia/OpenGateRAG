import httpx

from opengaterag.api.domain.user import AuthenticatedUserQuery
from opengaterag.api.domain.user.errors import UserNotAuthenticatedError
from opengaterag.api.domain.user.views import AuthenticatedUserView


class OpenGateLLMAuthenticatedUserQuery(AuthenticatedUserQuery):
    def __init__(self, opengatellm_client: httpx.AsyncClient):
        self.opengatellm_client = opengatellm_client

    async def get_user_by_api_key(self, api_key: str) -> AuthenticatedUserView | UserNotAuthenticatedError:
        response = await self.opengatellm_client.get(url="/v1/me", headers={"Authorization": f"Bearer {api_key}"})
        if response.status_code == 401:
            return UserNotAuthenticatedError()
        response.raise_for_status()

        return AuthenticatedUserView.model_validate(response.json())
