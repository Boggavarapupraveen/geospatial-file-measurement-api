"""
Main FastAPI Application Entry Point.
"""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import GeospatialAPIException
from app.api.files import router as files_router
from app.api.health import router as health_router
from app.api.samples import router as samples_router

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info("Ready to accept .zip (Shapefiles) and .kml geospatial uploads.")
    yield
    logger.info("Shutting down Geospatial API service.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Exception Handler
@app.exception_handler(GeospatialAPIException)
async def geospatial_exception_handler(request: Request, exc: GeospatialAPIException):
    logger.warning(f"Domain Exception: {exc.message} on path {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_type": exc.__class__.__name__},
    )


# API Routers
app.include_router(files_router, prefix=settings.API_PREFIX)
app.include_router(health_router, prefix=settings.API_PREFIX)
app.include_router(samples_router, prefix=settings.API_PREFIX)

# Static Files & Dashboard UI
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/dashboard", methods=["GET", "HEAD"], include_in_schema=False)
async def serve_dashboard():
    """Serves the interactive web dashboard."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"message": f"Welcome to {settings.PROJECT_NAME}. Visit /docs for API documentation."})
