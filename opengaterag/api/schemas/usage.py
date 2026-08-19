from pydantic import Field

from opengaterag.api.schemas import BaseModel


class EnvironmentalImpacts(BaseModel):
    kWh: float = 0.0
    kgCO2eq: float = 0.0


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    impacts: EnvironmentalImpacts = EnvironmentalImpacts()
