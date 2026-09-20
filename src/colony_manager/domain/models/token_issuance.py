"""Token issuance domain model for tracking issued JWT tokens.

This model tracks all issued tokens to enable bulk revocation and session management.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TokenIssuance(BaseModel):
    """Domain model for a token issuance record.

    Attributes:
        id: Database ID (None for new entries).
        user_id: ID of the user the token was issued to.
        token_id: The JWT jti claim (unique token identifier).
        token_type: Type of token ('access' or 'refresh').
        issued_at: When the token was issued.
        expires_at: When the token expires.
        revoked_at: When the token was revoked (None if still valid).
        ip_address: IP address from which the token was requested.
        user_agent: User agent string from the request.
    """

    id: int | None = None
    user_id: int = Field(..., gt=0)
    token_id: str = Field(..., min_length=1, max_length=255)
    token_type: str = Field(..., pattern="^(access|refresh)$")
    issued_at: datetime = Field(..., description="When the token was issued")
    expires_at: datetime = Field(..., description="When the token expires")
    revoked_at: datetime | None = Field(default=None, description="When the token was revoked")
    ip_address: str | None = Field(default=None, max_length=45)  # IPv6 max length
    user_agent: str | None = Field(default=None, max_length=500)
