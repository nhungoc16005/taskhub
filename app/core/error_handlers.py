from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core import messages
from app.core.constants import REQUEST_ID_HEADER
from app.core.exceptions import AppError


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    # ServerErrorMiddleware re-raises; Uvicorn owns the single traceback log.
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": messages.INTERNAL_SERVER_ERROR},
        headers={REQUEST_ID_HEADER: request_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, unexpected_error_handler)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
            headers=exc.headers,
        )
