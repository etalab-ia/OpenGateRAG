from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
import pytest

from opengaterag.api.helpers._accesscontroller import AccessController
from opengaterag.api.utils.context import request_context
from opengaterag.api.utils.exceptions import InvalidAPIKeyException, InvalidAuthenticationSchemeException


class TestAccessController:
    @pytest.fixture
    def access_controller(self):
        return AccessController()

    @pytest.fixture
    def mock_request(self):
        return MagicMock(spec=Request)

    @staticmethod
    def _api_key(credentials: str, scheme: str = "Bearer") -> HTTPAuthorizationCredentials:
        return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)

    @pytest.mark.asyncio
    async def test_invalid_scheme_raises(self, access_controller, mock_request):
        with pytest.raises(InvalidAuthenticationSchemeException):
            await access_controller(mock_request, self._api_key("sk-test", scheme="Basic"))

    @pytest.mark.asyncio
    async def test_empty_credentials_raises(self, access_controller, mock_request):
        with pytest.raises(InvalidAPIKeyException):
            await access_controller(mock_request, self._api_key(""))

    @pytest.mark.asyncio
    async def test_non_sk_prefix_raises(self, access_controller, mock_request):
        with pytest.raises(InvalidAPIKeyException):
            await access_controller(mock_request, self._api_key("invalid-key"))

    @pytest.mark.asyncio
    @patch("opengaterag.api.helpers._accesscontroller.httpx.AsyncClient")
    async def test_invalid_api_key_raises(self, mock_client_class, access_controller, mock_request):
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("Unauthorized")
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        with pytest.raises(InvalidAPIKeyException):
            await access_controller(mock_request, self._api_key("sk-invalid"))

    @pytest.mark.asyncio
    @patch("opengaterag.api.helpers._accesscontroller.httpx.AsyncClient")
    async def test_valid_api_key_sets_request_context(self, mock_client_class, access_controller, mock_request):
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"id": 42, "permissions": ["admin"]}
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        await access_controller(mock_request, self._api_key("sk-valid"))

        ctx = request_context.get()
        assert ctx.api_key == "sk-valid"
        assert ctx.user_id == 42
        assert ctx.user_permissions == ["admin"]
