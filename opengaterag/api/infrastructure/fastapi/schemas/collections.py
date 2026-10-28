from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from opengaterag.api.domain import BaseModel
from opengaterag.api.domain.collection.entities import CollectionVisibility
from opengaterag.api.infrastructure.fastapi.schemas import UnixTimestamp


class CreateCollectionBody(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1), Field(description="Name of the collection.", examples=["my-collection"])]  # fmt: off
    description: Annotated[str | None, Field(default=None, description="Description of the collection.")]
    visibility: Annotated[CollectionVisibility, Field(default=CollectionVisibility.PRIVATE, description="Public collections are readable by every user, private collections only by their owner. Making a collection public requires the right to do so.")]  # fmt: off


class CollectionResponse(BaseModel):
    object: Annotated[Literal["collection"], Field(default="collection", description="Type of the object.")]
    id: Annotated[int, Field(description="ID of the collection.")]
    user_id: Annotated[int, Field(description="ID of the user who owns the collection.")]
    name: Annotated[str, Field(description="Name of the collection.")]
    description: Annotated[str | None, Field(description="Description of the collection.")]
    visibility: Annotated[CollectionVisibility, Field(description="Visibility of the collection.")]
    documents: Annotated[int, Field(description="Number of documents in the collection.")]
    created: Annotated[UnixTimestamp, Field(description="Time of creation, as Unix timestamp.")]
    updated: Annotated[UnixTimestamp, Field(description="Time of last update, as Unix timestamp.")]
