from pydantic import BaseModel, Field


class ServiceCost(BaseModel):
    service: str
    monthly_cost: float
    percent_of_total: float


class CostSummary(BaseModel):
    total_monthly_cost: float
    by_service: list[ServiceCost] = Field(default_factory=list)
