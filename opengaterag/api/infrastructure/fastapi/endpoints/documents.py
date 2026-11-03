from fastapi import APIRouter, Depends, Path, Security

from opengaterag.api.dependencies import get_one_document_use_case_factory
from opengaterag.api.domain.document.errors import DocumentNotFoundError
from opengaterag.api.domain.user.views import AuthenticatedUserView
from opengaterag.api.infrastructure.fastapi.accesscontroller import AccessController
from opengaterag.api.infrastructure.fastapi.endpoints.exceptions import DocumentNotFoundHTTPException
from opengaterag.api.infrastructure.fastapi.routes import EndpointRoute, RouterName
from opengaterag.api.infrastructure.fastapi.schemas.documents import DocumentResponse
from opengaterag.api.use_cases.documents import GetOneDocumentCommand, GetOneDocumentUseCase, GetOneDocumentUseCaseSuccess

router = APIRouter(prefix="/v1", tags=[RouterName.DOCUMENTS.title()])


@router.get(path=EndpointRoute.DOCUMENT)
async def get_one_document(
    document_id: int = Path(description="ID of the document."),
    user: AuthenticatedUserView = Security(AccessController()),
    get_one_document_use_case: GetOneDocumentUseCase = Depends(get_one_document_use_case_factory),
) -> DocumentResponse:
    """
    Get a document from a collection you own or from a public collection.
    """
    command = GetOneDocumentCommand(user_id=user.id, document_id=document_id)
    result = await get_one_document_use_case.execute(command)

    match result:
        case GetOneDocumentUseCaseSuccess(document=document):
            return DocumentResponse.model_validate(document, from_attributes=True)
        case DocumentNotFoundError():
            raise DocumentNotFoundHTTPException()
