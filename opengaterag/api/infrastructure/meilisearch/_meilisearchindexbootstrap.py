import asyncio
from typing import Any

import httpx

from opengaterag.api.infrastructure.configuration import Configuration

MAX_BYTES_PER_CHARACTER = 4
COMPARED_EMBEDDER_FIELDS = ("source", "url", "request", "response", "dimensions", "documentTemplate", "documentTemplateMaxBytes")
FINISHED_TASK_STATUSES = ("succeeded", "failed", "canceled")
TASK_POLL_INTERVAL_SECONDS = 0.05


async def bootstrap_meilisearch_index(meilisearch_client: httpx.AsyncClient, configuration: Configuration) -> None:
    meilisearch = configuration.dependencies.meilisearch
    index_settings = build_index_settings(configuration)

    response = await meilisearch_client.get(f"/indexes/{meilisearch.index_name}/settings/embedders")
    if response.status_code == 404:
        # An index's tasks run in order, so the settings task below applies to this index. If another worker created it first, this task just fails.
        response = await meilisearch_client.post("/indexes", json={"uid": meilisearch.index_name, "primaryKey": "id"})
        response.raise_for_status()
        existing_embedders = {}
    else:
        response.raise_for_status()
        existing_embedders = response.json()

    # No embedder means the settings were never applied: the index is new, or a crashed start only got as far as creating it.
    if not existing_embedders:
        response = await meilisearch_client.patch(f"/indexes/{meilisearch.index_name}/settings", json=index_settings)
        response.raise_for_status()
        await wait_for_task(meilisearch_client, task_uid=response.json()["taskUid"], task_timeout=meilisearch.task_timeout)
        return

    differing_fields = get_differing_embedder_fields(
        expected_embedder=index_settings["embedders"][meilisearch.embedder_name],
        existing_embedder=existing_embedders.get(meilisearch.embedder_name, {}),
    )
    if differing_fields:
        raise RuntimeError(
            f"Embedder '{meilisearch.embedder_name}' of Meilisearch index '{meilisearch.index_name}' differs from the configuration: {', '.join(differing_fields)}. "
            "Applying these changes can re-embed every chunk, so a restart never does it: restore the configuration or update the index settings by hand."
        )  # fmt: off


def build_index_settings(configuration: Configuration) -> dict[str, Any]:
    meilisearch = configuration.dependencies.meilisearch
    opengatellm = configuration.dependencies.opengatellm

    index_settings = {
        "searchableAttributes": ["content"],
        "filterableAttributes": ["collection_id", "document_id", "metadata"],
        "embedders": {
            meilisearch.embedder_name: {
                "source": "rest",
                "url": meilisearch.embedder_url,
                "apiKey": meilisearch.embedder_api_key,
                "dimensions": opengatellm.model_vector_size,
                "request": {"model": opengatellm.model_name, "input": ["{{text}}", "{{..}}"]},
                "response": {"data": [{"embedding": "{{embedding}}"}, "{{..}}"]},
                "documentTemplate": "{{doc.content}}",
                "documentTemplateMaxBytes": configuration.settings.chunk_max_characters * MAX_BYTES_PER_CHARACTER,
            }
        },
    }
    if meilisearch.index_language:
        index_settings["localizedAttributes"] = [{"attributePatterns": ["content"], "locales": [meilisearch.index_language]}]

    return index_settings


def get_differing_embedder_fields(expected_embedder: dict[str, Any], existing_embedder: dict[str, Any]) -> list[str]:
    return [field for field in COMPARED_EMBEDDER_FIELDS if existing_embedder.get(field) != expected_embedder[field]]


async def wait_for_task(meilisearch_client: httpx.AsyncClient, task_uid: int, task_timeout: int) -> None:
    async with asyncio.timeout(task_timeout):
        while True:
            response = await meilisearch_client.get(f"/tasks/{task_uid}")
            response.raise_for_status()
            task = response.json()
            if task["status"] in FINISHED_TASK_STATUSES:
                break
            await asyncio.sleep(TASK_POLL_INTERVAL_SECONDS)

    if task["status"] != "succeeded":
        raise RuntimeError(f"Meilisearch task {task['uid']} ({task['type']}) ended as {task['status']}: {(task.get('error') or {}).get('message')}")
