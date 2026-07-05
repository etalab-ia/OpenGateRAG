from contextvars import ContextVar

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from opengaterag.api.helpers._accesscontroller import AccessController
from opengaterag.api.helpers._documentmanager import DocumentManager
from opengaterag.api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from opengaterag.api.schemas.search import CreateSearch, Searches
from opengaterag.api.utils.context import RequestContext
from opengaterag.api.utils.dependencies import (
    get_document_manager,
    get_elasticsearch_client,
    get_elasticsearch_vector_store,
    get_postgres_session,
    get_request_context,
)
from opengaterag.api.utils.variables import EndpointRoute, RouterName

router = APIRouter(prefix="/v1", tags=[RouterName.SEARCH.title()])


@router.post(path=EndpointRoute.SEARCH, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Searches)
async def search(
    request: Request,
    body: CreateSearch,
    postgres_session: AsyncSession = Depends(get_postgres_session),
    elasticsearch_vector_store: ElasticsearchVectorStore = Depends(get_elasticsearch_vector_store),
    elasticsearch_client: AsyncElasticsearch = Depends(get_elasticsearch_client),
    request_context: ContextVar[RequestContext] = Depends(get_request_context),
    document_manager: DocumentManager = Depends(get_document_manager),
) -> JSONResponse:
    """
    Get relevant chunks from the collections and a query.
    """
    data = await document_manager.search_chunks(
        postgres_session=postgres_session,
        elasticsearch_vector_store=elasticsearch_vector_store,
        elasticsearch_client=elasticsearch_client,
        request_context=request_context,
        collection_ids=body.collection_ids,
        document_ids=body.document_ids,
        metadata_filters=body.metadata_filters,
        query=body.query,
        method=body.method,
        limit=body.limit,
        offset=body.offset,
        rff_k=body.rff_k,
        score_threshold=body.score_threshold,
    )
    content = Searches(data=data)

    return JSONResponse(content=content.model_dump(mode="json"), status_code=200)
