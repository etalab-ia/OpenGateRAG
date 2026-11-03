from unittest.mock import create_autospec

from fastapi import FastAPI
from httpx import AsyncClient
import pytest

from opengaterag.api.dependencies import get_one_document_use_case_factory
from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.document.errors import DocumentNotFoundError
from opengaterag.api.infrastructure.fastapi.routes import EndpointRoute
from opengaterag.api.infrastructure.postgres.models import Collection as CollectionTable
from opengaterag.api.infrastructure.postgres.models import Document as DocumentTable
from opengaterag.api.tests.integration.endpoints.conftest import API_KEY, AUTHENTICATED_USER_ID
from opengaterag.api.use_cases.documents import GetOneDocumentUseCase

HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def _url(document_id: int) -> str:
    return f"/v1{EndpointRoute.DOCUMENT.format(document_id=document_id)}"


class TestGetOneDocument:
    async def test_should_get_document_of_own_collection(self, client: AsyncClient, db_session, mock_authenticated_user_query):
        # Arrange
        collection = CollectionTable(user_id=AUTHENTICATED_USER_ID, name="my-collection", description=None, visibility=CollectionVisibility.PRIVATE)  # fmt: off
        db_session.add(collection)
        await db_session.flush()
        document = DocumentTable(collection_id=collection.id, name="document.pdf")
        db_session.add(document)
        await db_session.flush()

        # Act
        response = await client.get(url=_url(document.id), headers=HEADERS)

        # Assert
        assert response.status_code == 200, response.text
        assert response.json()["id"] == document.id
        assert response.json()["collection_id"] == collection.id

    @pytest.mark.parametrize(
        "use_case_result,expected_status,expected_detail",
        [
            (DocumentNotFoundError(), 404, "Document not found."),
        ],
    )
    async def test_should_map_error_to_http_status(
        self, client: AsyncClient, app: FastAPI, mock_authenticated_user_query, use_case_result, expected_status, expected_detail
    ):
        # Arrange
        mock_use_case = create_autospec(GetOneDocumentUseCase, instance=True, spec_set=True)
        mock_use_case.execute.return_value = use_case_result
        app.dependency_overrides[get_one_document_use_case_factory] = lambda: mock_use_case

        # Act
        response = await client.get(url=_url(42), headers=HEADERS)

        # Assert
        assert response.status_code == expected_status, response.text
        assert response.json()["detail"] == expected_detail
