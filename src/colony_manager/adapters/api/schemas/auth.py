"""API schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Request schema for user login."""

    username: str = Field(
        ..., min_length=3, max_length=50, description="Your username", examples=["rogue_trader"]
    )
    password: str = Field(
        ..., min_length=8, max_length=128, description="Your password", examples=["SecureP@ss123"]
    )


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    username: str = Field(
        ..., min_length=3, max_length=50, description="Desired username", examples=["rogue_trader"]
    )
    email: EmailStr = Field(..., description="Your email address", examples=["trader@voidship.com"])
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description=(
            "Password (min 8 chars, must contain uppercase, lowercase, number, and special char)"
        ),
        examples=["SecureP@ss123"],
    )


class UserResponse(BaseModel):
    """Response schema for user information (excludes sensitive data)."""

    id: int
    username: str
    email: str
    role: str
    is_active: bool


class ChangePasswordRequest(BaseModel):
    """Request schema for changing password."""

    current_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class TokenRevokeRequest(BaseModel):
    """Request schema for token revocation (logout)."""

    reason: str | None = Field(None, max_length=100, description="Optional reason for revocation")


class TokenRevokeAllRequest(BaseModel):
    """Request schema for revoking all user tokens."""

    user_id: int | None = Field(
        None, gt=0, description="Target user ID (admin only). If omitted, revokes own tokens."
    )
    reason: str | None = Field(None, max_length=100, description="Optional reason for revocation")


class TokenRevokeResponse(BaseModel):
    """Response schema for token revocation."""

    message: str
    tokens_revoked: int = 0
