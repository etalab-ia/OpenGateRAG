from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx

from opengaterag.api.utils.configuration import configuration
from opengaterag.api.utils.context import RequestContext, request_context
from opengaterag.api.utils.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException


class AccessController:
    async def __call__(self, request: Request, api_key: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]):

        if api_key.scheme != "Bearer":
            raise InvalidAuthenticationSchemeException()

        if not api_key.credentials:
            raise InvalidAPIKeyException()

        if not api_key.credentials.startswith("sk-"):
            raise InvalidAPIKeyException()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=f"{configuration.dependencies.opengatellm.url}/v1/me/info",
                headers={"Authorization": f"Bearer {api_key.credentials}"},
                timeout=10,
            )
            try:
                response.raise_for_status()
            except Exception:
                raise InvalidAPIKeyException()

            data = response.json()

        request_context.set(RequestContext(api_key=api_key.credentials, user_id=data["id"], user_permissions=data["permissions"]))
