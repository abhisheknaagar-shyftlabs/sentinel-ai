import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IntegrationCreate(BaseModel):
    personal_access_token: str = Field(min_length=1)
    workspace_id: uuid.UUID | None = None


class IntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    account_login: str
    account_type: str
    scopes: str | None
    is_active: bool
    last_validated_at: datetime | None
    created_at: datetime
