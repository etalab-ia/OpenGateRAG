from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
import tiktoken
from tiktoken.core import Encoding

from opengaterag.api.helpers._documentmanager import DocumentManager
from opengaterag.api.helpers._elasticsearchvectorstore import ElasticsearchVectorStore
from opengaterag.api.helpers._parsermanager import ParserManager
from opengaterag.api.utils.configuration import Configuration, Tokenizer, get_configuration
from opengaterag.api.utils.context import global_context
from opengaterag.api.utils.logging import init_logger

logger = init_logger(name=__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configuration = get_configuration()

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{configuration.dependencies.opengatellm.url}/health", timeout=60)
        if response.status_code != 200:
            raise RuntimeError("OpenGateLLM is not reachable.")

    global_context.elasticsearch_client = await create_elasticsearch_client(configuration)
    global_context.postgres_engine, global_context.postgres_session_factory = create_postgres_session_factory(configuration)
    global_context.elasticsearch_vector_store = await create_elasticsearch_vector_store(configuration=configuration, elasticsearch_client=global_context.elasticsearch_client)  # fmt: off
    global_context.document_manager = create_document_manager(configuration=configuration)
    global_context.tokenizer = create_tokenizer(configuration=configuration)

    yield

    if global_context.elasticsearch_client:
        await global_context.elasticsearch_client.close()

    if global_context.postgres_engine:
        await global_context.postgres_engine.dispose()


async def create_elasticsearch_client(configuration: Configuration) -> AsyncElasticsearch | None:
    if configuration.dependencies.elasticsearch is None:
        return None

    kwargs = configuration.dependencies.elasticsearch.model_dump()
    kwargs.pop("index_name")
    kwargs.pop("index_language")
    kwargs.pop("number_of_shards")
    kwargs.pop("number_of_replicas")
    kwargs.pop("refresh_interval")

    client = AsyncElasticsearch(**kwargs)
    if not await client.ping():
        await client.close()
        raise RuntimeError("Elasticsearch database is not reachable.")
    return client


def create_tokenizer(configuration: Configuration) -> Encoding:
    match configuration.settings.usage_tokenizer:
        case Tokenizer.TIKTOKEN_O200K_BASE:
            return tiktoken.get_encoding("o200k_base")
        case Tokenizer.TIKTOKEN_P50K_BASE:
            return tiktoken.get_encoding("p50k_base")
        case Tokenizer.TIKTOKEN_R50K_BASE:
            return tiktoken.get_encoding("r50k_base")
        case Tokenizer.TIKTOKEN_P50K_EDIT:
            return tiktoken.get_encoding("p50k_edit")
        case Tokenizer.TIKTOKEN_CL100K_BASE:
            return tiktoken.get_encoding("cl100k_base")
        case Tokenizer.TIKTOKEN_GPT2:
            return tiktoken.get_encoding("gpt2")


def create_postgres_session_factory(configuration: Configuration) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(**configuration.dependencies.postgres.model_dump())
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


async def create_elasticsearch_vector_store(configuration: Configuration, elasticsearch_client: AsyncElasticsearch) -> ElasticsearchVectorStore:
    es_config = configuration.dependencies.elasticsearch
    vector_store = ElasticsearchVectorStore(index_name=es_config.index_name)
    await vector_store.setup(
        client=elasticsearch_client,
        index_language=es_config.index_language,
        number_of_shards=es_config.number_of_shards,
        number_of_replicas=es_config.number_of_replicas,
        vector_size=configuration.dependencies.opengatellm.model_vector_size,
        refresh_interval=es_config.refresh_interval,
    )
    return vector_store


def create_document_manager(configuration: Configuration) -> DocumentManager:
    parser_manager = ParserManager(max_concurrent=configuration.settings.document_parsing_max_concurrent)
    return DocumentManager(
        model_api_url=configuration.dependencies.opengatellm.url,
        model_name=configuration.dependencies.opengatellm.model_name,
        parser_manager=parser_manager,
    )
