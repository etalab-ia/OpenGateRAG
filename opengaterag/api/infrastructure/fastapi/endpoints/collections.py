from fastapi import APIRouter, Body, Depends, Path, Query, Security

from opengaterag.api.dependencies import (
    create_collection_use_case_factory,
    delete_collection_use_case_factory,
    get_collections_use_case_factory,
    get_one_collection_use_case_factory,
    update_collection_use_case_factory,
)
from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.domain.collection.errors import CollectionNotFoundError, PublicCollectionNotAllowedError
from opengaterag.api.domain.user.views import AuthenticatedUserView
from opengaterag.api.infrastructure.fastapi.accesscontroller import AccessController
from opengaterag.api.infrastructure.fastapi.endpoints.exceptions import CollectionNotFoundHTTPException, PublicCollectionNotAllowedHTTPException
from opengaterag.api.infrastructure.fastapi.routes import EndpointRoute, RouterName
from opengaterag.api.infrastructure.fastapi.schemas.collections import (
    CollectionResponse,
    CollectionsResponse,
    CreateCollectionBody,
    UpdateCollectionBody,
)
from opengaterag.api.use_cases.collections import (
    CreateCollectionCommand,
    CreateCollectionUseCase,
    CreateCollectionUseCaseSuccess,
    DeleteCollectionCommand,
    DeleteCollectionUseCase,
    DeleteCollectionUseCaseSuccess,
    GetCollectionsCommand,
    GetCollectionsUseCase,
    GetOneCollectionCommand,
    GetOneCollectionUseCase,
    GetOneCollectionUseCaseSuccess,
    UpdateCollectionCommand,
    UpdateCollectionUseCase,
    UpdateCollectionUseCaseSuccess,
)

router = APIRouter(prefix="/v1", tags=[RouterName.COLLECTIONS.title()])


@router.post(path=EndpointRoute.COLLECTIONS, status_code=201)
async def create_collection(
    body: CreateCollectionBody = Body(description="The collection creation request."),
    user: AuthenticatedUserView = Security(AccessController()),
    create_collection_use_case: CreateCollectionUseCase = Depends(create_collection_use_case_factory),
) -> CollectionResponse:
    """
    Create a collection.
    """
    command = CreateCollectionCommand(user_id=user.id, name=body.name, description=body.description, visibility=body.visibility)
    result = await create_collection_use_case.execute(command)

    match result:
        case CreateCollectionUseCaseSuccess(collection=collection):
            return CollectionResponse.model_validate(collection, from_attributes=True)
        case PublicCollectionNotAllowedError():
            raise PublicCollectionNotAllowedHTTPException()


@router.get(path=EndpointRoute.COLLECTIONS)
async def get_collections(
    name: str | None = Query(default=None, description="Return only the collections with exactly this name."),
    visibility: CollectionVisibility | None = Query(default=None, description="Return only the collections with this visibility."),
    offset: int = Query(default=0, ge=0, description="Number of collections to skip."),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of collections to return."),
    user: AuthenticatedUserView = Security(AccessController()),
    get_collections_use_case: GetCollectionsUseCase = Depends(get_collections_use_case_factory),
) -> CollectionsResponse:
    """
    Get the collections you own and the public collections.
    """
    command = GetCollectionsCommand(user_id=user.id, name=name, visibility=visibility, offset=offset, limit=limit)
    result = await get_collections_use_case.execute(command)

    return CollectionsResponse.model_validate(result, from_attributes=True)


@router.get(path=EndpointRoute.COLLECTION)
async def get_one_collection(
    collection_id: int = Path(description="ID of the collection."),
    user: AuthenticatedUserView = Security(AccessController()),
    get_one_collection_use_case: GetOneCollectionUseCase = Depends(get_one_collection_use_case_factory),
) -> CollectionResponse:
    """
    Get a collection you own or a public collection.
    """
    command = GetOneCollectionCommand(user_id=user.id, collection_id=collection_id)
    result = await get_one_collection_use_case.execute(command)

    match result:
        case GetOneCollectionUseCaseSuccess(collection=collection):
            return CollectionResponse.model_validate(collection, from_attributes=True)
        case CollectionNotFoundError():
            raise CollectionNotFoundHTTPException()


@router.patch(path=EndpointRoute.COLLECTION)
async def update_collection(
    collection_id: int = Path(description="ID of the collection."),
    body: UpdateCollectionBody = Body(description="The collection update request. Both fields are replaced."),
    user: AuthenticatedUserView = Security(AccessController()),
    update_collection_use_case: UpdateCollectionUseCase = Depends(update_collection_use_case_factory),
) -> CollectionResponse:
    """
    Update the name and description of a collection you own. Both fields are replaced.
    """
    command = UpdateCollectionCommand(user_id=user.id, collection_id=collection_id, name=body.name, description=body.description)
    result = await update_collection_use_case.execute(command)

    match result:
        case UpdateCollectionUseCaseSuccess(collection=collection):
            return CollectionResponse.model_validate(collection, from_attributes=True)
        case CollectionNotFoundError():
            raise CollectionNotFoundHTTPException()


@router.delete(path=EndpointRoute.COLLECTION, status_code=204)
async def delete_collection(
    collection_id: int = Path(description="ID of the collection."),
    user: AuthenticatedUserView = Security(AccessController()),
    delete_collection_use_case: DeleteCollectionUseCase = Depends(delete_collection_use_case_factory),
) -> None:
    """
    Delete a collection you own and its documents.
    """
    command = DeleteCollectionCommand(user_id=user.id, collection_id=collection_id)
    result = await delete_collection_use_case.execute(command)

    match result:
        case DeleteCollectionUseCaseSuccess():
            return None
        case CollectionNotFoundError():
            raise CollectionNotFoundHTTPException()
