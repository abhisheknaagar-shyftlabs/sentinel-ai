from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base for schemas served to the frontend adapter routers (app/api/frontend/).
    Serializes as camelCase to match frontend/API_CONTRACT.md exactly, while the
    rest of the codebase stays snake_case. Populate fields normally in Python
    (snake_case); FastAPI's response_model handles the camelCase conversion on
    the way out via by_alias serialization."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
