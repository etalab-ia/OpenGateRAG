import httpx
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


class GlobalContext(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    postgres_engine: AsyncEngine | None = None
    postgres_session_factory: async_sessionmaker | None = None
    opengatellm_client: httpx.AsyncClient | None = None


global_context: GlobalContext = GlobalContext.model_construct()
