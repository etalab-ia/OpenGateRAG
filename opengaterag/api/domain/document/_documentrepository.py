from abc import ABC, abstractmethod

from opengaterag.api.domain.document.entities import Document
from opengaterag.api.domain.document.errors import DocumentNotFoundError


class DocumentRepository(ABC):
    @abstractmethod
    async def get_document(self, document_id: int) -> Document | DocumentNotFoundError:
        pass
