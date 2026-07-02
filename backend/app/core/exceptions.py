from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.core.responses import error_envelope

logger = get_logger(__name__)


class AppException(Exception):
    code: str = "INTERNAL_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(AppException):
    code = "CONFLICT"
    status_code = status.HTTP_409_CONFLICT


class UnauthorizedError(AppException):
    code = "UNAUTHORIZED"
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(AppException):
    code = "FORBIDDEN"
    status_code = status.HTTP_403_FORBIDDEN


class ValidationAppError(AppException):
    code = "VALIDATION_ERROR"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


class ServiceUnavailableError(AppException):
    code = "SERVICE_UNAVAILABLE"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class GatewayTimeoutError(AppException):
    code = "GATEWAY_TIMEOUT"
    status_code = status.HTTP_504_GATEWAY_TIMEOUT


def register_exception_handlers(app) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_envelope("VALIDATION_ERROR", "Invalid request payload"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope("HTTP_ERROR", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", extra={"path": request.url.path})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_envelope("INTERNAL_ERROR", "An unexpected error occurred"),
        )
