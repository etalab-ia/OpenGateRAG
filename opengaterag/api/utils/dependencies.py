from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import Any

from elasticsearch import AsyncElasticsearch
from sqlalchemy.ext.asyncio import AsyncSession

from opengaterag.api.helpers._documentmanager import DocumentManager
from opengaterag.api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from opengaterag.api.utils.context import RequestContext, global_context, request_context


def get_document_manager() -> DocumentManager:
    return global_context.document_manager


def get_elasticsearch_client() -> AsyncElasticsearch:
    return global_context.elasticsearch_client


def get_elasticsearch_vector_store() -> ElasticsearchVectorStore:
    return global_context.elasticsearch_vector_store


async def get_postgres_session() -> AsyncGenerator[AsyncSession | Any, Any]:
    session_factory = global_context.postgres_session_factory
    async with session_factory() as postgres_session:
        yield postgres_session

        if postgres_session.in_transaction():
            await postgres_session.close()


def get_request_context() -> ContextVar[RequestContext]:
    return request_context
