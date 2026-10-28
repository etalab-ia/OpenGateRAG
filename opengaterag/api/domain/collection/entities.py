from enum import StrEnum

from opengaterag.api.domain import BaseModel, UtcDatetime


class CollectionVisibility(StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"


class Collection(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    visibility: CollectionVisibility
    created: UtcDatetime
    updated: UtcDatetime
