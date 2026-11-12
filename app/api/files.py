from typing import Any, Dict, List
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES
from app.models.schemas import (
    FeatureDetail,
    FileDetailResponse,
    FileInfo,
    FileListResponse,
    GeoJSONFeatureCollection,
)
from app.services.file_service import FileProcessingService

router = APIRouter(prefix="/api/files", tags=["Geospatial Files"])


@router.post(
    "/",
    response_model=FileInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a geospatial file",
    description="Accepts a `.kml` file or a `.zip` archive containing a Shapefile (.shp, .shx, .dbf, .prj).",
)
def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload.",
        )

    ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions are: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read content safely
    if hasattr(file, "file"):
        contents = file.file.read()
    else:
        contents = file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    # Process file
    detail = FileProcessingService.process_uploaded_file(file.filename, contents)

    # Return FileInfo
    return FileInfo(
        id=detail.id,
        filename=detail.filename,
        file_type=detail.file_type,
        feature_count=detail.feature_count,
        crs=detail.crs,
        status=detail.status,
        geometry_summary=detail.geometry_summary,
        created_at=detail.created_at,
        error_message=detail.error_message,
    )


@router.get(
    "/",
    response_model=FileListResponse,
    summary="List all uploaded geospatial files",
)
def list_files():
    files = FileProcessingService.list_files()
    return FileListResponse(total=len(files), files=files)


@router.get(
    "/{file_id}/",
    response_model=FileInfo,
    summary="Get summary information for an uploaded file",
    description="Returns metadata, feature count, CRS, and status for the given file ID.",
)
def get_file_info(file_id: str):
    record = FileProcessingService.get_file(file_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{file_id}' not found.",
        )
    return FileInfo(
        id=record.id,
        filename=record.filename,
        file_type=record.file_type,
        feature_count=record.feature_count,
        crs=record.crs,
        status=record.status,
        geometry_summary=record.geometry_summary,
        created_at=record.created_at,
        error_message=record.error_message,
    )


@router.get(
    "/{file_id}/details/",
    response_model=FileDetailResponse,
    summary="Get complete file details including all features and measurements",
)
def get_file_details(file_id: str):
    record = FileProcessingService.get_file(file_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{file_id}' not found.",
        )
    return record


@router.get(
    "/{file_id}/features/",
    response_model=List[FeatureDetail],
    summary="Get all features with measurements and properties",
)
def get_features(file_id: str):
    record = FileProcessingService.get_file(file_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{file_id}' not found.",
        )
    return record.features


@router.get(
    "/{file_id}/features/{feature_id}/",
    response_model=FeatureDetail,
    summary="Get a specific feature by its ID",
)
def get_feature_by_id(file_id: str, feature_id: str):
    record = FileProcessingService.get_file(file_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{file_id}' not found.",
        )
    for feat in record.features:
        if str(feat.id) == str(feature_id):
            return feat

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Feature with ID '{feature_id}' not found in file '{file_id}'.",
    )


@router.get(
    "/{file_id}/geojson/",
    response_model=GeoJSONFeatureCollection,
    summary="Export features as a standard GeoJSON FeatureCollection",
)
def get_geojson(file_id: str):
    geojson = FileProcessingService.get_geojson(file_id)
    if not geojson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{file_id}' not found or processing failed.",
        )
    return geojson


@router.delete(
    "/{file_id}/",
    status_code=status.HTTP_200_OK,
    summary="Delete an uploaded file record",
)
def delete_file(file_id: str):
    deleted = FileProcessingService.delete_file(file_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{file_id}' not found.",
        )
    return {"message": f"File '{file_id}' successfully deleted."}
