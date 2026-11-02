from unittest.mock import create_autospec

from fastapi import FastAPI
from httpx import AsyncClient
import pytest

from opengaterag.api.dependencies import get_one_collection_use_case_factory
from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.infrastructure.fastapi.routes import EndpointRoute
from opengaterag.api.infrastructure.postgres.models import Collection as CollectionTable
from opengaterag.api.infrastructure.postgres.models import Document as DocumentTable
from opengaterag.api.tests.integration.endpoints.conftest import API_KEY, AUTHENTICATED_USER_ID
from opengaterag.api.use_cases.collections import GetOneCollectionUseCase

HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def _url(collection_id: int) -> str:
    return f"/v1{EndpointRoute.COLLECTION.format(collection_id=collection_id)}"


class TestGetOneCollection:
    async def test_should_get_own_collection(self, client: AsyncClient, db_session, mock_authenticated_user_query):
        # Arrange
        collection = CollectionTable(user_id=AUTHENTICATED_USER_ID, name="my-collection", description=None, visibility=CollectionVisibility.PRIVATE)  # fmt: off
        db_session.add(collection)
        await db_session.flush()
        db_session.add(DocumentTable(collection_id=collection.id, name="document.pdf"))
        await db_session.flush()

        # Act
        response = await client.get(url=_url(collection.id), headers=HEADERS)

        # Assert
        assert response.status_code == 200, response.text
        assert response.json()["id"] == collection.id
        assert response.json()["documents"] == 1

    async def test_should_hide_private_collection_of_another_user(self, client: AsyncClient, db_session, mock_authenticated_user_query):
        # Arrange
        collection = CollectionTable(user_id=AUTHENTICATED_USER_ID + 1, name="other-collection", description=None, visibility=CollectionVisibility.PRIVATE)  # fmt: off
        db_session.add(collection)
        await db_session.flush()

        # Act
        response = await client.get(url=_url(collection.id), headers=HEADERS)

        # Assert
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == "Collection not found."

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (CollectionNotFoundError(collection_id=7), 404, "Collection not found."),
        ],
    )
    async def test_should_map_error_to_http_status(
        self, client: AsyncClient, app: FastAPI, mock_authenticated_user_query, use_case_result, expected_status, expected_detail
    ):
        # Arrange
        mock_use_case = create_autospec(GetOneCollectionUseCase, instance=True, spec_set=True)
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[get_one_collection_use_case_factory] = lambda: mock_use_case

        # Act
        response = await client.get(url=_url(7), headers=HEADERS)

        # Assert
        assert response.status_code == expected_status, response.text
        assert response.json()["detail"] == expected_detail
