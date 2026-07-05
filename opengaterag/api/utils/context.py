from contextvars import ContextVar
from typing import Any

from pydantic import BaseModel


class GlobalContext(BaseModel):
    document_manager: Any = None
    elasticsearch_vector_store: Any = None
    elasticsearch_client: Any = None
    postgres_session_factory: Any = None
    postgres_engine: Any = None
    tokenizer: Any = None


class RequestContext(BaseModel):
    api_key: str
    user_id: int | None


global_context: GlobalContext = GlobalContext.model_construct()
request_context: ContextVar[RequestContext] = ContextVar("request_context", default=RequestContext.model_construct())
