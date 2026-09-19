"""Health check endpoint for the API."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Check if the API is running and healthy.

    Returns:
        Simple status response indicating the API is operational.
    """
    return {"status": "healthy"}
