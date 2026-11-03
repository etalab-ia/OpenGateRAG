from sqlalchemy import delete, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from opengaterag.api.domain.collection import CollectionRepository
from opengaterag.api.domain.collection.entities import Collection, CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
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

    async def update_collection(self, collection_id: int, name: str, description: str | None) -> Collection | CollectionNotFoundError:
        statement = update(CollectionTable).where(CollectionTable.id == collection_id).values(name=name, description=description).returning(CollectionTable)  # fmt: off
        row = (await self.postgres_session.execute(statement)).scalar_one_or_none()

        if row is None:
            return CollectionNotFoundError()

        return Collection.model_validate(row, from_attributes=True)

    async def delete_collection(self, collection_id: int) -> None | CollectionNotFoundError:
        statement = delete(CollectionTable).where(CollectionTable.id == collection_id).returning(CollectionTable.id)
        deleted_id = (await self.postgres_session.execute(statement)).scalar_one_or_none()

        if deleted_id is None:
            return CollectionNotFoundError()

        return None
