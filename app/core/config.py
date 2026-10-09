"""
Application Configuration Settings.
"""
from pathlib import Path
from typing import List, Set
from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "Geospatial File Measurement API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = (
        "Production-grade backend service to process Shapefile and KML files, "
        "reproject coordinates to optimal projected CRS, and calculate precise geometric measurements."
    )
    API_PREFIX: str = "/api"
    
    # Upload & Storage settings
    UPLOAD_DIR: Path = Path("./uploads")
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: Set[str] = {".zip", ".kml"}
    
    # Default CRS if not specified in dataset
    DEFAULT_GEOGRAPHIC_CRS: str = "EPSG:4326"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]


settings = Settings()

# Ensure upload directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
