import logging
from time import sleep
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from opengaterag.api.schemas.search import Searches
from opengaterag.api.utils.variables import EndpointRoute

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def collection_id(user_client: TestClient):
    # Create a collection
    response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json={"name": f"test_collection_{uuid4()}"})
    assert response.status_code == 201, response.text
    collection_id = response.json()["id"]

    yield collection_id

    # delete the collection
    response = user_client.delete(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
    assert response.status_code == 204, response.text


@pytest.fixture(scope="function")
def document_id(user_client: TestClient, collection_id: int):
    # create a document
    data = {"collection_id": collection_id, "name": "test_search_document.pdf"}
    response = user_client.post(url=f"/v1{EndpointRoute.DOCUMENTS}", data=data)
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]

    yield document_id

    # delete the document
    response = user_client.delete(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}")
    assert response.status_code == 204, response.text


@pytest.fixture(scope="function")
def chunks_ids(user_client: TestClient, document_id: int):
    data = {
        "chunks": [
            {"content": "Qui est Albert ?", "metadata": {"source_title": "test", "source_page": "1"}},
            {"content": "Qui est Erasmus ?", "metadata": {"source_title": "test", "source_page": "2"}},
            {"content": "Qui est Voltaire ?", "metadata": {"source_title": "test", "source_page": "3"}},
        ]
    }
    response = user_client.post(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks", json=data)
    assert response.status_code == 201, response.text
    chunk_ids = response.json()["ids"]
    sleep(2)

    yield chunk_ids


@pytest.mark.usefixtures("user_client", "admin_client", "collection_id", "document_id", "chunks_ids")
class TestSearch:
    @staticmethod
    def _create_document_with_chunk(user_client: TestClient, collection_id: int, chunks: list[dict] = []) -> int:
        response = user_client.post(url=f"/v1{EndpointRoute.DOCUMENTS}", data={"collection_id": collection_id, "name": "test.pdf"})
        assert response.status_code == 201, response.text
        document_id = response.json()["id"]

        if chunks:
            response = user_client.post(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks", json={"chunks": chunks})
            assert response.status_code == 201, response.text
            sleep(2)

        return document_id

    def test_search_with_pagination_limit(self, user_client: TestClient, admin_client: TestClient, document_id: int, chunks_ids: list[int]):
        """Test the POST /search with pagination limit."""

        data = {"query": "Qui est Albert ?", "limit": 2}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)

        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        assert len(searches.data) == 2
        assert all(search.chunk.id in chunks_ids for search in searches.data)
        search = searches.data[0]
        assert search.chunk.document_id == document_id

    def test_search_with_pagination_offset(self, user_client: TestClient, admin_client: TestClient):
        """Test the POST /search with pagination offset."""

        data = {"query": "Qui est Albert ?", "limit": 2, "offset": 0}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        assert len(searches.data) == 2
        first_chunk_id = searches.data[0].chunk.id
        second_chunk_id = searches.data[1].chunk.id

        data = {"query": "Qui est Albert ?", "limit": 2, "offset": 1}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        assert len(searches.data) == 1  # only one chunk left
        assert searches.data[0].chunk.id == second_chunk_id
        assert first_chunk_id not in [search.chunk.id for search in searches.data]

    def test_search_with_legacy_query_argument(self, user_client: TestClient, admin_client: TestClient):
        """Test POST /search with a legacy query argument."""

        data = {"prompt": "Voltaire", "limit": 1}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        assert len(searches.data) == 1
        assert searches.data[0].chunk.content == "Qui est Voltaire ?"

    def test_search_with_score_threshold(self, user_client: TestClient, admin_client: TestClient):
        """Test POST /search with a score threshold."""

        data = {"query": "Voltaire", "limit": 3}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        first_chunk_id = searches.data[0].chunk.id

        first_score = searches.data[0].score
        second_score = searches.data[1].score
        third_score = searches.data[2].score
        assert first_score >= second_score >= third_score

        data = {"query": "Voltaire", "limit": 3, "score_threshold": first_score}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        assert len(searches.data) == 1
        assert searches.data[0].chunk.id == first_chunk_id

    def test_search_with_invalid_collection(self, user_client: TestClient, admin_client: TestClient):
        """Test search with an invalid collection."""
        data = {"query": "Erasmus", "collection_ids": [100], "limit": 3}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 404, response.text

    def test_search_with_empty_query(self, user_client: TestClient, admin_client: TestClient):
        """Test POST /search with an empty prompt."""
        data = {"query": "", "limit": 3}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 422, response.text

    def test_search_with_collection_ids_filter(self, user_client: TestClient, collection_id: int):
        # create a collection, document and chunks
        response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json={"name": f"test_collection_{uuid4()}"})
        assert response.status_code == 201, response.text
        second_collection_id = response.json()["id"]

        self._create_document_with_chunk(user_client=user_client, collection_id=second_collection_id, chunks=[{"content": "Test"}])

        data = {"query": "Test", "limit": 100}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        assert collection_id in [search.chunk.collection_id for search in searches.data]
        assert second_collection_id in [search.chunk.collection_id for search in searches.data]

        data = {"query": "Test", "collection_ids": [collection_id], "limit": 10}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        assert collection_id in [search.chunk.collection_id for search in searches.data]
        assert second_collection_id not in [search.chunk.collection_id for search in searches.data]

        # legacy alias: collections
        data = {"query": "Test", "collections": [collection_id], "limit": 10}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        assert collection_id in [search.chunk.collection_id for search in searches.data]
        assert second_collection_id not in [search.chunk.collection_id for search in searches.data]

    def test_search_with_document_ids_filter(self, user_client: TestClient, admin_client: TestClient, collection_id: int, document_id: int):
        # create a document and chunks
        second_document_id = self._create_document_with_chunk(user_client=user_client, collection_id=collection_id, chunks=[{"content": "Test"}])

        data = {"query": "Test", "document_ids": [document_id], "limit": 10}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        assert document_id in [search.chunk.document_id for search in searches.data]
        assert second_document_id not in [search.chunk.document_id for search in searches.data]

        data = {"query": "Test", "document_ids": [document_id], "limit": 10}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        assert document_id in [search.chunk.document_id for search in searches.data]
        assert second_document_id not in [search.chunk.document_id for search in searches.data]

    @pytest.mark.parametrize(
        "filter_type,filter_value",
        [("eq", "secondary title"), ("sw", "sec"), ("ew", "le"), ("co", "dary ti")],
        ids=["eq", "sw", "ew", "co"],
    )
    def test_search_with_metadata_comparison_filters(
        self,
        user_client: TestClient,
        collection_id: int,
        document_id: int,
        filter_type: str,
        filter_value: str | int,
    ):
        second_document_id = self._create_document_with_chunk(
            user_client=user_client,
            collection_id=collection_id,
            chunks=[
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "secondary title", "source_page": 1}},
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "secondary title", "source_page": 1}},
            ],
        )

        data = {
            "query": "Qui est",
            "limit": 10,
            "metadata_filters": {"key": "source_title", "type": filter_type, "value": filter_value},
        }
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())

        assert len(searches.data) >= 1
        assert all(search.chunk.document_id == second_document_id for search in searches.data)
        assert document_id not in [search.chunk.document_id for search in searches.data]

    def test_search_with_metadata_compound_filter_and(self, user_client: TestClient, admin_client: TestClient, collection_id: int, document_id: int):
        second_document_id = self._create_document_with_chunk(
            user_client=user_client,
            collection_id=collection_id,
            chunks=[
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "test", "source_page": "42"}},
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "test", "source_page": "42"}},
            ],
        )

        data = {
            "query": "Qui est",
            "method": "lexical",
            "limit": 10,
            "metadata_filters": {
                "filters": [
                    {"key": "source_title", "type": "eq", "value": "test"},
                    {"key": "source_page", "type": "eq", "value": "42"},
                ],
                "operator": "and",
            },
        }
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())

        assert len(searches.data) >= 1
        assert all(search.chunk.document_id == second_document_id for search in searches.data)
        assert document_id not in [search.chunk.document_id for search in searches.data]

    def test_search_with_metadata_compound_filter_or(self, user_client: TestClient, admin_client: TestClient, collection_id: int):
        second_document_id = self._create_document_with_chunk(
            user_client=user_client,
            collection_id=collection_id,
            chunks=[
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "test", "source_page": "42"}},
                {"content": "Qui est Test Secondary ?", "metadata": {"source_title": "test", "source_page": "42"}},
            ],
        )

        data = {
            "query": "Qui est",
            "method": "lexical",
            "limit": 10,
            "metadata_filters": {
                "filters": [
                    {"key": "source_page", "type": "eq", "value": "1"},
                    {"key": "source_page", "type": "eq", "value": "42"},
                ],
                "operator": "or",
            },
        }
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())

        search_document_ids = {search.chunk.document_id for search in searches.data}
        assert len(searches.data) >= 2
        assert second_document_id in search_document_ids
        assert document_id not in search_document_ids
        assert any(search.chunk.metadata and str(search.chunk.metadata["source_page"]) == "1" for search in searches.data)

    def test_search_with_access_other_user_collection(self, user_client: TestClient, admin_client: TestClient):
        """Test POST /search with access to other user's collection."""

        # create a collection, document and chunks with a different user
        response = admin_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json={"name": f"test_collection_{uuid4()}"})
        assert response.status_code == 201, response.text
        collection_id = response.json()["id"]

        response = admin_client.post(url=f"/v1{EndpointRoute.DOCUMENTS}", data={"collection_id": collection_id, "name": "test.pdf"})
        assert response.status_code == 201, response.text
        document_id = response.json()["id"]

        response = admin_client.post(url=f"/v1{EndpointRoute.DOCUMENTS}/{document_id}/chunks", json={"chunks": [{"content": "Test"}]})
        assert response.status_code == 201, response.text
        chunk_id = response.json()["ids"][0]

        data = {"query": "What is the largest planet in our solar system?", "collection_ids": [collection_id], "limit": 10}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 404, response.text

        data = {"query": "What is the largest planet in our solar system?", "limit": 10}
        response = user_client.post(url=f"/v1{EndpointRoute.SEARCH}", json=data)
        assert response.status_code == 200, response.text
        searches = Searches(**response.json())
        assert document_id not in [search.chunk.document_id for search in searches.data]
