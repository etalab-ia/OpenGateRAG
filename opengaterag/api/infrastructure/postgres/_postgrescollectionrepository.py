from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from opengaterag.api.domain.collection import CollectionRepository
from opengaterag.api.domain.collection.entities import Collection, CollectionVisibility
from opengaterag.api.infrastructure.postgres.models import Collection as CollectionTable


class PostgresCollectionRepository(CollectionRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def create_collection(self, user_id: int, name: str, description: str | None, visibility: CollectionVisibility) -> Collection:
        statement = (
            insert(CollectionTable).values(user_id=user_id, name=name, description=description, visibility=visibility).returning(CollectionTable)
        )
        result = await self.postgres_session.execute(statement)

        return Collection.model_validate(result.scalar_one(), from_attributes=True)
