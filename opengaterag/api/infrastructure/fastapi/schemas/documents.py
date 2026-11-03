from typing import Annotated, Literal

from pydantic import Field

from opengaterag.api.domain import BaseModel
from opengaterag.api.infrastructure.fastapi.schemas import UnixTimestamp


class DocumentResponse(BaseModel):
    object: Annotated[Literal["document"], Field(default="document", description="Type of the object.")]
    id: Annotated[int, Field(description="ID of the document.")]
    collection_id: Annotated[int, Field(description="ID of the collection that contains the document.")]
    name: Annotated[str, Field(description="Name of the document.")]
    created: Annotated[UnixTimestamp, Field(description="Time of creation, as Unix timestamp.")]
