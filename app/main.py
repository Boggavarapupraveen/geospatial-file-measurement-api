from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.files import router as files_router
from app.config import APP_DESCRIPTION, APP_NAME, SAMPLES_DIR, STATIC_DIR, VERSION
from app.samples.sample_generator import generate_samples
from app.services.file_service import FileProcessingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("geo_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes existing storage and ensures sample test files exist."""
    logger.info("Initializing Geospatial File Measurement API...")
    FileProcessingService.initialize()

    # Ensure samples exist
    kml_sample = SAMPLES_DIR / "sample_survey.kml"
    shp_sample = SAMPLES_DIR / "sample_shapefile.zip"
    if not kml_sample.exists() or not shp_sample.exists():
        logger.info("Generating sample geospatial datasets...")
        generate_samples(SAMPLES_DIR)
    logger.info("Service started successfully.")
    yield
    logger.info("Service shutting down.")


app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Geospatial Files",
            "description": "Endpoints for uploading, extracting, measuring, and querying geospatial files.",
        },
        {
            "name": "Samples & Utility",
            "description": "Download pre-bundled test geospatial datasets (Shapefile & KML) and health checks.",
        },
    ],
)

# Enable CORS for cross-origin frontend or API clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(files_router)

# Mount static web directory
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serves the interactive GIS web explorer."""
    index_path = STATIC_DIR / "index.html"
    return FileResponse(str(index_path))


@app.get("/health", tags=["Samples & Utility"])
async def health_check():
    """Health status check endpoint."""
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": VERSION,
    }


@app.get(
    "/api/samples/kml",
    tags=["Samples & Utility"],
    summary="Download pre-bundled sample KML file",
)
async def get_sample_kml():
    """Returns a realistic sample KML file with Polygon, LineString, and Point features."""
    sample_path = SAMPLES_DIR / "sample_survey.kml"
    if not sample_path.exists():
        generate_samples(SAMPLES_DIR)
    return FileResponse(
        str(sample_path),
        media_type="application/vnd.google-earth.kml+xml",
        filename="sample_survey.kml",
    )


@app.get(
    "/api/samples/shapefile",
    tags=["Samples & Utility"],
    summary="Download pre-bundled sample Shapefile (.zip)",
)
async def get_sample_shapefile():
    """Returns a realistic sample zipped Shapefile archive containing .shp, .shx, .dbf, and .prj."""
    sample_path = SAMPLES_DIR / "sample_shapefile.zip"
    if not sample_path.exists():
        generate_samples(SAMPLES_DIR)
    return FileResponse(
        str(sample_path),
        media_type="application/zip",
        filename="sample_shapefile.zip",
    )
