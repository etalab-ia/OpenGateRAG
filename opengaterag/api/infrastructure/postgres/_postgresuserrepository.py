from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from opengaterag.api.domain.user import UserRepository
from opengaterag.api.domain.user.entities import User
from opengaterag.api.infrastructure.postgres.models import User as UserTable


class PostgresUserRepository(UserRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_or_create_user(self, user_id: int, storage_limit: int | None) -> User:
        await self.postgres_session.execute(
            insert(UserTable).values(id=user_id, storage_limit=storage_limit).on_conflict_do_nothing(index_elements=[UserTable.id])
        )
        row = await self.postgres_session.scalar(select(UserTable).where(UserTable.id == user_id))

        return User.model_validate(row, from_attributes=True)
