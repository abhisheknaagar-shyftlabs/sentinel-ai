import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RepositoryTrackRequest(BaseModel):
    full_name: str = Field(min_length=1, description="owner/repo")


class TrackedRepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    integration_id: uuid.UUID
    github_id: int
    name: str
    full_name: str
    private: bool
    default_branch: str
    html_url: str
    description: str | None
    last_synced_at: datetime | None
    created_at: datetime
