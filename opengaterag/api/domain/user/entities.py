from opengaterag.api.domain import BaseModel, UtcDatetime


class User(BaseModel):
    id: int
    storage_limit: int | None
    create_public_collection: bool
    created: UtcDatetime
    updated: UtcDatetime
