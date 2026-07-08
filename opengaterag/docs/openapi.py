import copy

import httpx


def merge_openapi_schemas(
    base: dict,
    secondary: dict,
    secondary_server_url: str,
    secondary_path_prefix: str = "",
) -> dict:
    """
    Merge a `secondary` OpenAPI schema into a `base` one and return the result.

    - `secondary` paths are served by another origin, so a per-operation `servers` entry pointing to
      `secondary_server_url` is added (unless the operation already declares one).
    - Component schemas keep their original names; on a name collision the `base` definition is kept.
    - Tags of both schemas keep their original names (operations sharing a tag name are grouped together)
      and the resulting top-level `tags` list is sorted alphabetically so Swagger UI and ReDoc display the
      routers in alphabetical order.
    """
    merged = copy.deepcopy(base)
    secondary = copy.deepcopy(secondary)

    merged.setdefault("paths", {})
    for path, path_item in secondary.get("paths", {}).items():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            operation.setdefault("servers", [{"url": secondary_server_url}])
        merged["paths"][f"{secondary_path_prefix}{path}"] = path_item

    merged_components = merged.setdefault("components", {})
    for section, values in secondary.get("components", {}).items():
        if isinstance(values, dict):
            target = merged_components.setdefault(section, {})
            for name, definition in values.items():
                target.setdefault(name, definition)

    merged["tags"] = _sorted_tags(merged, secondary)

    return merged


def _sorted_tags(merged: dict, secondary: dict) -> list[dict]:
    """Build a de-duplicated, alphabetically sorted top-level `tags` list from both schemas."""
    tag_objects: dict[str, dict] = {}
    for tag in merged.get("tags", []) + secondary.get("tags", []):
        name = tag.get("name")
        if name is not None:
            tag_objects.setdefault(name, tag)

    for path_item in merged.get("paths", {}).values():
        for operation in path_item.values():
            if isinstance(operation, dict):
                for name in operation.get("tags", []):
                    tag_objects.setdefault(name, {"name": name})

    return sorted(tag_objects.values(), key=lambda tag: tag["name"].lower())


async def fetch_openapi_schema(url: str, timeout: float = 10.0) -> dict:
    """Fetch a remote OpenAPI schema. Raises `httpx.HTTPError` if the service is unreachable or errors."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
