from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


RESOURCE_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Invalid operation or assignee"},
    401: {"model": ErrorResponse, "description": "Authentication required"},
    403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    404: {"model": ErrorResponse, "description": "Resource not found or not visible"},
    409: {"model": ErrorResponse, "description": "Archived project or data conflict"},
}
