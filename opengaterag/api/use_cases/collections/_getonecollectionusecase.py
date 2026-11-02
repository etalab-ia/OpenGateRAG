from dataclasses import dataclass

from opengaterag.api.domain.collection import CollectionQuery
from opengaterag.api.domain.collection.errors import CollectionNotFoundError
from opengaterag.api.domain.collection.views import CollectionView


@dataclass
class GetOneCollectionCommand:
    user_id: int
    collection_id: int


@dataclass
class GetOneCollectionUseCaseSuccess:
    collection: CollectionView


type GetOneCollectionUseCaseResult = GetOneCollectionUseCaseSuccess | CollectionNotFoundError


class GetOneCollectionUseCase:
    def __init__(self, collection_query: CollectionQuery):
        self.collection_query = collection_query

    async def execute(self, command: GetOneCollectionCommand) -> GetOneCollectionUseCaseResult:
        result = await self.collection_query.get_collection(collection_id=command.collection_id)

        match result:
            case CollectionNotFoundError():
                return result
            case CollectionView() as collection if not collection.is_readable_by(user_id=command.user_id):
                return CollectionNotFoundError(collection_id=command.collection_id)
            case CollectionView() as collection:
                return GetOneCollectionUseCaseSuccess(collection=collection)
