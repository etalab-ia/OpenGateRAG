from dataclasses import dataclass

from opengaterag.api.domain.collection import CollectionQuery
from opengaterag.api.domain.collection.views import CollectionView


@dataclass
class GetCollectionsCommand:
    user_id: int
    offset: int
    limit: int


@dataclass
class GetCollectionsUseCaseSuccess:
    data: list[CollectionView]
    total: int
    offset: int
    limit: int


class GetCollectionsUseCase:
    def __init__(self, collection_query: CollectionQuery):
        self.collection_query = collection_query

    async def execute(self, command: GetCollectionsCommand) -> GetCollectionsUseCaseSuccess:
        collections, total = await self.collection_query.get_readable_collections(
            user_id=command.user_id,
            offset=command.offset,
            limit=command.limit,
        )

        return GetCollectionsUseCaseSuccess(data=collections, total=total, offset=command.offset, limit=command.limit)
