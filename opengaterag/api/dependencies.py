from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from opengaterag.api.domain.user import AuthenticatedUserQuery
from opengaterag.api.infrastructure.configuration import Configuration, get_configuration
from opengaterag.api.infrastructure.context import global_context
from opengaterag.api.infrastructure.opengatellm import OpenGateLLMAuthenticatedUserQuery
from opengaterag.api.infrastructure.postgres import (
    PostgresCollectionQuery,
    PostgresCollectionRepository,
    PostgresDocumentRepository,
    PostgresUserRepository,
)
from opengaterag.api.use_cases.collections import (
    CreateCollectionUseCase,
    DeleteCollectionUseCase,
    GetCollectionsUseCase,
    GetOneCollectionUseCase,
    UpdateCollectionUseCase,
)
from opengaterag.api.use_cases.documents import GetOneDocumentUseCase


async def get_postgres_session() -> AsyncGenerator[AsyncSession]:
    session_factory = global_context.postgres_session_factory
    async with session_factory() as postgres_session:
        try:
            yield postgres_session
            if postgres_session.in_transaction():
                await postgres_session.commit()
        except Exception:
            if postgres_session.in_transaction():
                await postgres_session.rollback()
            raise


def get_authenticated_user_query() -> AuthenticatedUserQuery:
    return OpenGateLLMAuthenticatedUserQuery(opengatellm_client=global_context.opengatellm_client)


# collection use cases
def create_collection_use_case_factory(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    configuration: Configuration = Depends(get_configuration),
) -> CreateCollectionUseCase:
    return CreateCollectionUseCase(
        user_repository=PostgresUserRepository(postgres_session=postgres_session),
        collection_repository=PostgresCollectionRepository(postgres_session=postgres_session),
        storage_default_limit=configuration.settings.storage_default_limit,
    )


def get_collections_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetCollectionsUseCase:
    return GetCollectionsUseCase(collection_query=PostgresCollectionQuery(postgres_session=postgres_session))


def get_one_collection_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetOneCollectionUseCase:
    return GetOneCollectionUseCase(collection_query=PostgresCollectionQuery(postgres_session=postgres_session))


def update_collection_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> UpdateCollectionUseCase:
    return UpdateCollectionUseCase(
        collection_repository=PostgresCollectionRepository(postgres_session=postgres_session),
        collection_query=PostgresCollectionQuery(postgres_session=postgres_session),
    )


def delete_collection_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> DeleteCollectionUseCase:
    return DeleteCollectionUseCase(
        collection_repository=PostgresCollectionRepository(postgres_session=postgres_session),
        collection_query=PostgresCollectionQuery(postgres_session=postgres_session),
    )


# document use cases
def get_one_document_use_case_factory(postgres_session: AsyncSession = Depends(get_postgres_session)) -> GetOneDocumentUseCase:
    return GetOneDocumentUseCase(
        document_repository=PostgresDocumentRepository(postgres_session=postgres_session),
        collection_query=PostgresCollectionQuery(postgres_session=postgres_session),
    )
