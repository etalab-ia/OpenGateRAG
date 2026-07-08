import time

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
import httpx

from opengaterag.api.utils.configuration import Configuration
from opengaterag.api.utils.logging import init_logger
from opengaterag.docs.openapi import fetch_openapi_schema, merge_openapi_schemas

logger = init_logger(name=__name__)

OPENAPI_CACHE_TTL_SECONDS = 300


def create_docs_app(parent_app: FastAPI, configuration: Configuration) -> FastAPI:
    """
    Build a lightweight FastAPI sub-application that serves a single, unified Swagger UI and ReDoc.

    It merges the OpenAPI schema of the host application (`parent_app`, OpenGateRAG) with the schema of
    the remote OpenGateLLM service (fetched from its `url`). If OpenGateLLM is unreachable, only the
    OpenGateRAG schema is served so the documentation never fully breaks.
    """
    settings = configuration.settings
    opengatellm_url = configuration.dependencies.opengatellm.url.rstrip("/")
    opengatellm_openapi_path = configuration.dependencies.opengatellm.openapi_url.lstrip("/")
    opengatellm_openapi_url = f"{opengatellm_url}/{opengatellm_openapi_path}"

    docs_app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    cache: dict[str, object] = {"schema": None, "expires_at": 0.0}

    async def build_merged_schema() -> dict:
        now = time.monotonic()
        if cache["schema"] is not None and now < cache["expires_at"]:
            return cache["schema"]

        base_schema = parent_app.openapi()
        try:
            secondary_schema = await fetch_openapi_schema(url=opengatellm_openapi_url)
            merged = merge_openapi_schemas(
                base=base_schema,
                secondary=secondary_schema,
                secondary_server_url=opengatellm_url,
            )
        except httpx.HTTPError as error:
            logger.warning(f"Unable to fetch OpenGateLLM OpenAPI schema from {opengatellm_openapi_url}: {error}")
            merged = base_schema

        cache["schema"] = merged
        cache["expires_at"] = now + OPENAPI_CACHE_TTL_SECONDS
        return merged

    @docs_app.get(path=settings.swagger_openapi_url, include_in_schema=False)
    async def openapi() -> JSONResponse:
        return JSONResponse(content=await build_merged_schema())

    @docs_app.get(path=settings.swagger_docs_url, include_in_schema=False)
    async def swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=settings.swagger_openapi_url,
            title=f"{settings.app_title} - Swagger UI",
            swagger_ui_parameters={"tagsSorter": "alpha"},
        )

    @docs_app.get(path=settings.swagger_redoc_url, include_in_schema=False)
    async def redoc() -> HTMLResponse:
        return get_redoc_html(openapi_url=settings.swagger_openapi_url, title=f"{settings.app_title} - ReDoc")

    return docs_app
