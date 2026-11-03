from dataclasses import dataclass

from opengaterag.api.domain.collection import CollectionQuery, CollectionRepository
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView


@dataclass
class DeleteCollectionCommand:
    user_id: int
    collection_id: int


@dataclass
class DeleteCollectionUseCaseSuccess:
    pass


type DeleteCollectionUseCaseResult = DeleteCollectionUseCaseSuccess | CollectionNotFoundError


class DeleteCollectionUseCase:
    def __init__(self, collection_repository: CollectionRepository, collection_query: CollectionQuery):
        self.collection_repository = collection_repository
        self.collection_query = collection_query

    async def execute(self, command: DeleteCollectionCommand) -> DeleteCollectionUseCaseResult:
        collection = await self.collection_query.get_collection(collection_id=command.collection_id)

        match collection:
            case CollectionNotFoundError():
                return collection
            case CollectionView() if not collection.is_writable_by(user_id=command.user_id):
                return CollectionNotFoundError()

        deleted = await self.collection_repository.delete_collection(collection_id=command.collection_id)

        match deleted:
            case CollectionNotFoundError():
                return deleted
            case None:
                return DeleteCollectionUseCaseSuccess()
