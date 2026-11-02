from fastapi import APIRouter, Body, Depends, Path, Security

from opengaterag.api.dependencies import create_collection_use_case_factory, get_one_collection_use_case_factory
from opengaterag.api.domain.collection.errors import CollectionNotFoundError, PublicCollectionNotAllowedError
from opengaterag.api.domain.user.views import AuthenticatedUserView
from opengaterag.api.infrastructure.fastapi.accesscontroller import AccessController
from opengaterag.api.infrastructure.fastapi.endpoints.exceptions import CollectionNotFoundHTTPException, PublicCollectionNotAllowedHTTPException
from opengaterag.api.infrastructure.fastapi.routes import EndpointRoute, RouterName
from opengaterag.api.infrastructure.fastapi.schemas.collections import CollectionResponse, CreateCollectionBody
from opengaterag.api.use_cases.collections import (
    CreateCollectionCommand,
    CreateCollectionUseCase,
    CreateCollectionUseCaseSuccess,
    GetOneCollectionCommand,
    GetOneCollectionUseCase,
    GetOneCollectionUseCaseSuccess,
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
