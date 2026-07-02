from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class AgentExecutionResult(BaseModel, Generic[T]):
    agent_name: str
    success: bool
    data: T | None = None
    error: str | None = None
    error_type: str | None = None
    duration_ms: float
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
