from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str = ""
    timestamp: str = ""


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    timestamp: str = ""


def success_envelope(data: Any = None, message: str = "") -> dict:
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": utc_now_iso(),
    }


def error_envelope(code: str, message: str) -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message},
        "timestamp": utc_now_iso(),
    }
