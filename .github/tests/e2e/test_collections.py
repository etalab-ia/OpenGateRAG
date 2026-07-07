import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from opengaterag.api.schemas.collections import Collection, Collections, CollectionVisibility
from opengaterag.api.utils.variables import EndpointRoute


@pytest.mark.usefixtures("user_client", "admin_client")
class TestCollections:
    def test_create_private_collection(self, user_client: TestClient, admin_client: TestClient):
        params = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE}
        response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}")
        assert response.status_code == 200, response.text

        collections = response.json()
        Collections(**collections)  # test output format

        collections = [collection for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 1

        collection = collections[0]
        assert collection["name"] == params["name"]
        assert collection["visibility"] == CollectionVisibility.PRIVATE

    def test_get_one_collection(self, user_client: TestClient, admin_client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["name"] == collection_name

    def test_patch_collection_name(self, user_client: TestClient, admin_client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]
        new_collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": new_collection_name}
        response = user_client.patch(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}", json=params)
        assert response.status_code == 204, response.text

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["name"] == new_collection_name

    def test_format_collection(self, user_client: TestClient, admin_client: TestClient):
        params = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE}
        response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text
        collection_id = response.json()["id"]

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}")
        assert response.status_code == 200, response.text

        collections = response.json()
        Collections(**collections)  # test output format

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        Collection(**collection)  # test output format

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        Collection(**collection)  # test output format

    def test_create_public_collection_without_permissions(self, user_client: TestClient, admin_client: TestClient):
        params = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PUBLIC}
        response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 403, response.text

    def test_patch_public_collection_without_permissions(self, user_client: TestClient, admin_client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        params = {"visibility": CollectionVisibility.PUBLIC}
        response = user_client.patch(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}", json=params)
        assert response.status_code == 403, response.text

    def test_create_public_collection_with_permissions(self, user_client: TestClient, admin_client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC}
        response = admin_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}")
        assert response.status_code == 200, response.text

        collections = response.json()
        collections = [collection for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 1

        collection = collections[0]
        assert collection["name"] == collection_name
        assert collection["visibility"] == CollectionVisibility.PUBLIC

    def test_patch_public_collection_with_permissions(self, user_client: TestClient, admin_client: TestClient):
        collection_name = f"test_collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = admin_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        params = {"visibility": CollectionVisibility.PUBLIC}
        response = admin_client.patch(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}", json=params)
        assert response.status_code == 204, response.text

    def test_view_collection_of_other_user(self, user_client: TestClient, admin_client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = admin_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 404, response.text

    def test_view_public_collection_of_other_user(self, user_client: TestClient, admin_client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC}
        response = admin_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

    def test_delete_private_collection_without_permissions(self, user_client: TestClient, admin_client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = user_client.delete(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 204

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}")
        collections = response.json()
        assert response.status_code == 200, response.text

        collections = [collection for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 0

    def test_delete_public_collection_without_permissions(self, user_client: TestClient, admin_client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC}
        response = admin_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        collections = response.json()
        assert response.status_code == 200, response.text

        response = user_client.delete(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 404, response.text

    def test_delete_public_collection_with_permissions(self, user_client: TestClient, admin_client: TestClient):
        collection_name = f"test-collection_{str(uuid4())}"
        params = {"name": collection_name, "visibility": CollectionVisibility.PUBLIC}
        response = admin_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = admin_client.delete(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 204, response.text

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}")
        collections = response.json()
        assert response.status_code == 200, response.text

        collections = [collection["id"] for collection in collections["data"] if collection["id"] == collection_id]
        assert len(collections) == 0

    def test_create_collection_with_empty_name(self, user_client: TestClient, admin_client: TestClient):
        collection_name = " "
        params = {"name": collection_name, "visibility": CollectionVisibility.PRIVATE}
        response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 422, response.text

    def test_create_collection_with_description(self, user_client: TestClient, admin_client: TestClient):
        params = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE, "description": "test-description"}
        response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()

        assert collection["description"] == params["description"]

    def test_update_collection_updated(self, user_client: TestClient, admin_client: TestClient):
        params = {"name": f"test_collection_{str(uuid4())}", "visibility": CollectionVisibility.PRIVATE}
        response = user_client.post(url=f"/v1{EndpointRoute.COLLECTIONS}", json=params)
        assert response.status_code == 201, response.text

        collection_id = response.json()["id"]

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["updated"] is not None
        updated = collection["updated"]

        time.sleep(1)

        response = user_client.patch(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}", json={"description": "test-description"})
        assert response.status_code == 204, response.text

        response = user_client.get(url=f"/v1{EndpointRoute.COLLECTIONS}/{collection_id}")
        assert response.status_code == 200, response.text

        collection = response.json()
        assert collection["updated"] is not None
        assert collection["updated"] > updated
