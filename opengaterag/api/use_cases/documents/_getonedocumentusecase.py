from dataclasses import dataclass

from opengaterag.api.domain.collection import CollectionQuery
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView
from opengaterag.api.domain.document import DocumentRepository
from opengaterag.api.domain.document.entities import Document
from opengaterag.api.domain.document.errors import DocumentNotFoundError


@dataclass
class GetOneDocumentCommand:
    user_id: int
    document_id: int


@dataclass
class GetOneDocumentUseCaseSuccess:
    document: Document


type GetOneDocumentUseCaseResult = GetOneDocumentUseCaseSuccess | DocumentNotFoundError


class GetOneDocumentUseCase:
    def __init__(self, document_repository: DocumentRepository, collection_query: CollectionQuery):
        self.document_repository = document_repository
        self.collection_query = collection_query

    async def execute(self, command: GetOneDocumentCommand) -> GetOneDocumentUseCaseResult:
        document = await self.document_repository.get_document(document_id=command.document_id)

        match document:
            case DocumentNotFoundError():
                return document

        collection = await self.collection_query.get_collection(collection_id=document.collection_id)

        match collection:
            case CollectionNotFoundError():
                return DocumentNotFoundError()
            case CollectionView() if not collection.is_readable_by(user_id=command.user_id):
                return DocumentNotFoundError()
            case CollectionView():
                return GetOneDocumentUseCaseSuccess(document=document)
