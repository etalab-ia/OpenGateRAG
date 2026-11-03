from opengaterag.api.domain import BaseModel, UtcDatetime


class Document(BaseModel):
    id: int
    collection_id: int
    name: str
    created: UtcDatetime
