from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opengaterag.api.domain.document import DocumentRepository
from opengaterag.api.domain.document.entities import Document
from opengaterag.api.domain.document.errors import DocumentNotFoundError
from opengaterag.api.infrastructure.postgres.models import Document as DocumentTable


class PostgresDocumentRepository(DocumentRepository):
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_document(self, document_id: int) -> Document | DocumentNotFoundError:
        statement = select(DocumentTable).where(DocumentTable.id == document_id)
        row = (await self.postgres_session.execute(statement)).scalar_one_or_none()

        if row is None:
            return DocumentNotFoundError()

        return Document.model_validate(row, from_attributes=True)
