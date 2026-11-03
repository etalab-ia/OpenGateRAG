from unittest.mock import create_autospec

from fastapi import FastAPI
from httpx import AsyncClient
import pytest
from sqlalchemy import select

from opengaterag.api.dependencies import delete_collection_use_case_factory
from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.infrastructure.fastapi.routes import EndpointRoute
from opengaterag.api.infrastructure.postgres.models import Collection as CollectionTable
from opengaterag.api.tests.integration.endpoints.conftest import API_KEY, AUTHENTICATED_USER_ID
from opengaterag.api.use_cases.collections import DeleteCollectionUseCase

HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def _url(collection_id: int) -> str:
    return f"/v1{EndpointRoute.COLLECTION.format(collection_id=collection_id)}"


class TestDeleteCollection:
    async def test_should_delete_own_collection(self, client: AsyncClient, db_session, mock_authenticated_user_query):
        # Arrange
        collection = CollectionTable(user_id=AUTHENTICATED_USER_ID, name="my-collection", description=None, visibility=CollectionVisibility.PRIVATE)
        db_session.add(collection)
        await db_session.flush()

        # Act
        response = await client.delete(url=_url(collection.id), headers=HEADERS)

        # Assert
        assert response.status_code == 204, response.text
        assert await db_session.scalar(select(CollectionTable.id).where(CollectionTable.id == collection.id)) is None

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (CollectionNotFoundError(), 404, "Collection not found."),
        ],
    )
    async def test_should_map_error_to_http_status(
        self, client: AsyncClient, app: FastAPI, mock_authenticated_user_query, use_case_result, expected_status, expected_detail
    ):
        # Arrange
        mock_use_case = create_autospec(DeleteCollectionUseCase, instance=True, spec_set=True)
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[delete_collection_use_case_factory] = lambda: mock_use_case

        # Act
        response = await client.delete(url=_url(7), headers=HEADERS)

        # Assert
        assert response.status_code == expected_status, response.text
        assert response.json()["detail"] == expected_detail
