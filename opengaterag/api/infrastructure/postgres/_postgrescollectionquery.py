from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opengaterag.api.domain.collection import CollectionQuery
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView
from opengaterag.api.infrastructure.postgres.models import Collection as CollectionTable
from opengaterag.api.infrastructure.postgres.models import Document as DocumentTable


class PostgresCollectionQuery(CollectionQuery):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_collection(self, collection_id: int) -> CollectionView | CollectionNotFoundError:
        documents = select(func.count()).select_from(DocumentTable).where(DocumentTable.collection_id == CollectionTable.id).scalar_subquery()
        statement = select(*CollectionTable.__table__.columns, documents.label("documents")).where(CollectionTable.id == collection_id)
        row = (await self.postgres_session.execute(statement)).one_or_none()

        if row is None:
            return CollectionNotFoundError(collection_id=collection_id)

        return CollectionView.model_validate(row, from_attributes=True)
