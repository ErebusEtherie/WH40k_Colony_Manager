"""Login attempt domain model for account lockout protection.

This model tracks failed login attempts to enable brute force protection.
Accounts are locked after N failed attempts within a time window.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class LoginAttempt(BaseModel):
    """Domain model for a login attempt record.

    Attributes:
        id: Database ID (None for new entries).
        username: The username that was attempted (for tracking per-account).
        ip_address: IP address of the attempt (for tracking per-IP).
        attempted_at: When the attempt occurred.
        success: Whether the login was successful.
        user_agent: Optional user agent string for auditing.
    """

    id: int | None = None
    username: str = Field(..., min_length=1, max_length=50)
    ip_address: str | None = Field(default=None, max_length=45)  # IPv6 max length
    attempted_at: datetime = Field(..., description="When the attempt occurred")
    success: bool = Field(default=False, description="Whether login succeeded")
    user_agent: str | None = Field(default=None, max_length=500)
