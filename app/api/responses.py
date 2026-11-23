from typing import Any

from pydantic import BaseModel, ConfigDict


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"detail": "Resource not found"}]}
    )
    detail: str


class ValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str
    input: Any = None
    ctx: dict[str, Any] | None = None


class ValidationErrorResponse(BaseModel):
    detail: list[ValidationIssue]


ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid operation or assignee"},
    401: {"model": ErrorResponse, "description": "Authentication required"},
    403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    404: {"model": ErrorResponse, "description": "Resource not found or not visible"},
    409: {"model": ErrorResponse, "description": "Archived project or data conflict"},
    422: {
        "model": ValidationErrorResponse,
        "description": "Invalid request body, path, query or form data",
    },
    500: {
        "model": ErrorResponse,
        "description": "Unexpected server error; details are logged internally",
    },
}


def error_responses(*status_codes: int) -> dict:
    return {code: ERROR_RESPONSES[code] for code in status_codes}


RESOURCE_RESPONSES = error_responses(400, 401, 403, 404, 409, 422, 500)
