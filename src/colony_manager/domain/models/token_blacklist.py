"""Token blacklist domain model.

This model represents revoked JWT tokens that should be rejected even if
cryptographically valid. Tokens are blacklisted when:
- User explicitly logs out (token revocation)
- User changes password (all tokens revoked)
- Admin revokes user's tokens (compromised account, etc.)
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TokenBlacklist(BaseModel):
    """Domain model for a blacklisted JWT token.

    Attributes:
        id: Database ID (None for new entries).
        token_id: The JWT 'jti' claim value - unique identifier for the token.
        user_id: ID of the user who owned this token (for bulk revocation).
        expires_at: When the token would have naturally expired.
        revoked_at: When the token was revoked/blacklisted.
        reason: Why the token was revoked (e.g., "logout", "password_change",
            "admin_revoke", "compromised").
    """

    id: int | None = None
    token_id: str = Field(..., min_length=1, description="JWT jti claim value")
    user_id: int = Field(..., gt=0, description="User ID who owned this token")
    expires_at: datetime = Field(..., description="Token's natural expiration time")
    revoked_at: datetime = Field(..., description="When token was blacklisted")
    reason: str | None = Field(default=None, description="Reason for revocation")
