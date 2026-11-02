from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from opengaterag.api.domain.collection import CollectionQuery
from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView
from opengaterag.api.infrastructure.postgres.models import Collection as CollectionTable
from opengaterag.api.infrastructure.postgres.models import Document as DocumentTable


class PostgresCollectionQuery(CollectionQuery):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_collection(self, collection_id: int) -> CollectionView | CollectionNotFoundError:
        statement = self._select_collection_views().where(CollectionTable.id == collection_id)
        row = (await self.postgres_session.execute(statement)).one_or_none()

        if row is None:
            return CollectionNotFoundError()

        return CollectionView.model_validate(row, from_attributes=True)

    async def get_readable_collections(self, user_id: int, name: str | None, visibility: CollectionVisibility | None, offset: int, limit: int) -> tuple[list[CollectionView], int]:  # fmt: off
        filters = [or_(CollectionTable.user_id == user_id, CollectionTable.visibility == CollectionVisibility.PUBLIC)]
        if name is not None:
            filters.append(CollectionTable.name == name)
        if visibility is not None:
            filters.append(CollectionTable.visibility == visibility)

        total = await self.postgres_session.scalar(select(func.count()).select_from(CollectionTable).where(*filters))
        statement = self._select_collection_views().where(*filters).order_by(CollectionTable.id).offset(offset).limit(limit)
        rows = (await self.postgres_session.execute(statement)).all()

        return [CollectionView.model_validate(row, from_attributes=True) for row in rows], total

    @staticmethod
    def _select_collection_views() -> Select:
        documents = select(func.count()).select_from(DocumentTable).where(DocumentTable.collection_id == CollectionTable.id).scalar_subquery()

        return select(*CollectionTable.__table__.columns, documents.label("documents"))
