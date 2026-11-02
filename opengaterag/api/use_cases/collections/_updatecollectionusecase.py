from dataclasses import dataclass

from opengaterag.api.domain.collection import CollectionQuery, CollectionRepository
from opengaterag.api.domain.collection.entities import Collection
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView


@dataclass
class UpdateCollectionCommand:
    user_id: int
    collection_id: int
    name: str
    description: str | None


@dataclass
class UpdateCollectionUseCaseSuccess:
    collection: CollectionView


type UpdateCollectionUseCaseResult = UpdateCollectionUseCaseSuccess | CollectionNotFoundError


class UpdateCollectionUseCase:
    def __init__(self, collection_repository: CollectionRepository, collection_query: CollectionQuery):
        self.collection_repository = collection_repository
        self.collection_query = collection_query

    async def execute(self, command: UpdateCollectionCommand) -> UpdateCollectionUseCaseResult:
        collection = await self.collection_query.get_collection(collection_id=command.collection_id)

        match collection:
            case CollectionNotFoundError():
                return collection
            case CollectionView() if not collection.is_writable_by(user_id=command.user_id):
                return CollectionNotFoundError()

        updated = await self.collection_repository.update_collection(
            collection_id=command.collection_id,
            name=command.name,
            description=command.description,
        )

        match updated:
            case CollectionNotFoundError():
                return updated
            case Collection():
                return UpdateCollectionUseCaseSuccess(collection=CollectionView(**updated.model_dump(), documents=collection.documents))
