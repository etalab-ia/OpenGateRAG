from pydantic import BaseModel, ConfigDict


class AuthenticatedUserView(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
