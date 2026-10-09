"""
Health and Status Endpoints.
"""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Service Health Check")
async def health_check():
    """Returns application health and configuration metadata."""
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "allowed_formats": list(settings.ALLOWED_EXTENSIONS),
        "max_file_size_mb": settings.MAX_FILE_SIZE_BYTES // (1024 * 1024),
    }
