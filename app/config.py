import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SAMPLES_DIR = BASE_DIR / "app" / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = BASE_DIR / "app" / "static"

APP_NAME = "Geospatial File Measurement API"
APP_DESCRIPTION = (
    "Production-ready backend API and interactive web application for accepting, "
    "processing, reprojection-based measurement, and visualization of Shapefiles and KML files."
)
VERSION = "1.0.0"

ALLOWED_EXTENSIONS = {".zip", ".kml"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

