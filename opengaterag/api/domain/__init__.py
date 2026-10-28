from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict


class BaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


def _to_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(tz=UTC)


UtcDatetime = Annotated[datetime, AfterValidator(_to_utc)]
