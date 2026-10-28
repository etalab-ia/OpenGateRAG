from dataclasses import dataclass

from opengaterag.api.domain.collection import CollectionRepository
from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.collection.errors import PublicCollectionNotAllowedError
from opengaterag.api.domain.collection.views import CollectionView
from opengaterag.api.domain.user import UserRepository


@dataclass
class CreateCollectionCommand:
    user_id: int
    name: str
    description: str | None
    visibility: CollectionVisibility


@dataclass
class CreateCollectionUseCaseSuccess:
    collection: CollectionView


type CreateCollectionUseCaseResult = CreateCollectionUseCaseSuccess | PublicCollectionNotAllowedError


class CreateCollectionUseCase:
    def __init__(self, user_repository: UserRepository, collection_repository: CollectionRepository, storage_default_limit: int | None):
        self.user_repository = user_repository
        self.collection_repository = collection_repository
        self.storage_default_limit = storage_default_limit

    async def execute(self, command: CreateCollectionCommand) -> CreateCollectionUseCaseResult:
        user = await self.user_repository.get_or_create_user(user_id=command.user_id, storage_limit=self.storage_default_limit)

        if command.visibility == CollectionVisibility.PUBLIC and not user.create_public_collection:
            return PublicCollectionNotAllowedError(user_id=user.id)

        collection = await self.collection_repository.create_collection(
            user_id=user.id,
            name=command.name,
            description=command.description,
            visibility=command.visibility,
        )

        return CreateCollectionUseCaseSuccess(collection=CollectionView(**collection.model_dump(), documents=0))
