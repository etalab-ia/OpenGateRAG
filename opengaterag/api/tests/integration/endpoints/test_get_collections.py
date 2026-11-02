from httpx import AsyncClient

from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.infrastructure.fastapi.routes import EndpointRoute
from opengaterag.api.infrastructure.postgres.models import Collection as CollectionTable
from opengaterag.api.infrastructure.postgres.models import Document as DocumentTable
from opengaterag.api.tests.integration.endpoints.conftest import API_KEY, AUTHENTICATED_USER_ID

HEADERS = {"Authorization": f"Bearer {API_KEY}"}
URL = f"/v1{EndpointRoute.COLLECTIONS}"


class TestGetCollections:
    async def test_should_get_paginated_list_of_readable_collections(self, client: AsyncClient, db_session, mock_authenticated_user_query):
        # Arrange
        own = CollectionTable(user_id=AUTHENTICATED_USER_ID, name="own", description=None, visibility=CollectionVisibility.PRIVATE)
        public = CollectionTable(user_id=AUTHENTICATED_USER_ID + 1, name="public", description=None, visibility=CollectionVisibility.PUBLIC)
        hidden = CollectionTable(user_id=AUTHENTICATED_USER_ID + 1, name="hidden", description=None, visibility=CollectionVisibility.PRIVATE)
        db_session.add_all([own, public, hidden])
        await db_session.flush()
        db_session.add(DocumentTable(collection_id=own.id, name="document.pdf"))
        await db_session.flush()

        # Act
        response = await client.get(url=URL, headers=HEADERS, params={"offset": 0, "limit": 1})

        # Assert
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["object"] == "list"
        assert (body["total"], body["offset"], body["limit"]) == (2, 0, 1)
        assert [collection["id"] for collection in body["data"]] == [own.id]
        assert body["data"][0]["object"] == "collection"
        assert body["data"][0]["documents"] == 1

    async def test_should_filter_collections_by_name_and_visibility(self, client: AsyncClient, db_session, mock_authenticated_user_query):
        # Arrange
        match = CollectionTable(user_id=AUTHENTICATED_USER_ID, name="wanted", description=None, visibility=CollectionVisibility.PRIVATE)
        other_name = CollectionTable(user_id=AUTHENTICATED_USER_ID, name="other", description=None, visibility=CollectionVisibility.PRIVATE)
        other_visibility = CollectionTable(user_id=AUTHENTICATED_USER_ID, name="wanted", description=None, visibility=CollectionVisibility.PUBLIC)
        db_session.add_all([match, other_name, other_visibility])
        await db_session.flush()

        # Act
        response = await client.get(url=URL, headers=HEADERS, params={"name": "wanted", "visibility": "private"})

        # Assert
        assert response.status_code == 200, response.text
        assert [collection["id"] for collection in response.json()["data"]] == [match.id]
