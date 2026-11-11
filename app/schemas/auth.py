from pydantic import BaseModel, Field

from app.core.constants import TOKEN_TYPE_BEARER


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="Short-lived JWT used to call the API")
    refresh_token: str = Field(
        ..., description="Long-lived JWT used to get a new access token"
    )
    token_type: str = Field(TOKEN_TYPE_BEARER, description="Token type, always bearer")


class AccessTokenResponse(BaseModel):
    access_token: str = Field(..., description="New short-lived JWT")
    token_type: str = Field(TOKEN_TYPE_BEARER, description="Token type, always bearer")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="The refresh token issued at login")
