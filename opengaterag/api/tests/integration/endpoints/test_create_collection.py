from unittest.mock import create_autospec

from fastapi import FastAPI
from httpx import AsyncClient
import pytest

from opengaterag.api.dependencies import create_collection_use_case_factory
from opengaterag.api.domain.collection.errors import PublicCollectionNotAllowedError
from opengaterag.api.domain.user.errors import UserNotAuthenticatedError
from opengaterag.api.infrastructure.fastapi.routes import EndpointRoute
from opengaterag.api.tests.integration.endpoints.conftest import API_KEY, AUTHENTICATED_USER_ID
from opengaterag.api.use_cases.collections import CreateCollectionUseCase

URL = f"/v1{EndpointRoute.COLLECTIONS}"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


class TestCreateCollection:
    async def test_should_create_private_collection(self, client: AsyncClient, mock_authenticated_user_query):
        # Act
        response = await client.post(url=URL, headers=HEADERS, json={"name": "  my-collection  ", "description": "My documents."})

        # Assert
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["object"] == "collection"
        assert isinstance(data["id"], int)
        assert data["user_id"] == AUTHENTICATED_USER_ID
        assert data["name"] == "my-collection"
        assert data["description"] == "My documents."
        assert data["visibility"] == "private"
        assert data["documents"] == 0
        assert isinstance(data["created"], int)
        assert isinstance(data["updated"], int)
        mock_authenticated_user_query.get_user_by_api_key.assert_awaited_once_with(api_key=API_KEY)

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (PublicCollectionNotAllowedError(user_id=AUTHENTICATED_USER_ID), 403, "You are not allowed to make a collection public."),
        ],
    )
    async def test_should_map_error_to_http_status(
        self, client: AsyncClient, app: FastAPI, mock_authenticated_user_query, use_case_result, expected_status, expected_detail
    ):
        # Arrange
        mock_use_case = create_autospec(CreateCollectionUseCase, instance=True, spec_set=True)
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[create_collection_use_case_factory] = lambda: mock_use_case

        # Act
        response = await client.post(url=URL, headers=HEADERS, json={"name": "my-collection", "visibility": "public"})

        # Assert
        assert response.status_code == expected_status, response.text
        assert response.json()["detail"] == expected_detail

    async def test_should_reject_request_without_api_key(self, client: AsyncClient, mock_authenticated_user_query):
        # Act
        response = await client.post(url=URL, json={"name": "my-collection"})

        # Assert
        assert response.status_code == 401, response.text
        assert response.json()["detail"] == "Not authenticated"
        mock_authenticated_user_query.get_user_by_api_key.assert_not_awaited()

    async def test_should_reject_invalid_api_key(self, client: AsyncClient, mock_authenticated_user_query):
        # Arrange
        mock_authenticated_user_query.get_user_by_api_key.return_value = UserNotAuthenticatedError()

        # Act
        response = await client.post(url=URL, headers=HEADERS, json={"name": "my-collection"})

        # Assert
        assert response.status_code == 401, response.text
        assert response.json()["detail"] == "Invalid API key."

    @pytest.mark.parametrize("body", [{}, {"name": "   "}, {"name": "my-collection", "visibility": "shared"}])
    async def test_should_reject_invalid_body(self, client: AsyncClient, mock_authenticated_user_query, body):
        # Act
        response = await client.post(url=URL, headers=HEADERS, json=body)

        # Assert
        assert response.status_code == 422, response.text
