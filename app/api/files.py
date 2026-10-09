"""
Geospatial Files and Measurements API Router.
"""
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    GeospatialAPIException,
    FileNotFoundInStorageException,
)
from app.models.file_models import (
    FileInfoResponse,
    FileUploadResponse,
    FileListResponse,
)
from app.models.measurement_models import FileMeasurementsResponse
from app.services.file_processor import file_processor
from app.services.storage_service import storage_service

router = APIRouter(prefix="/files", tags=["Geospatial Files"])


@router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload & Process Geospatial File",
    description="Accepts a zipped ESRI Shapefile (.zip) or a Keyhole Markup Language (.kml) file, "
                "extracts features, reprojects to optimal projected CRS, and computes measurements.",
)
async def upload_file(
    file: UploadFile = File(..., description="Zipped Shapefile (.zip) or KML (.kml) file")
):
    try:
        response = await file_processor.process_uploaded_file(file)
        return response
    except GeospatialAPIException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected internal error occurred during file processing: {str(e)}",
        )


@router.get(
    "/",
    response_model=FileListResponse,
    summary="List All Uploaded Files",
    description="Returns metadata for all uploaded geospatial files in storage.",
)
async def list_files():
    all_files = storage_service.list_files()
    return FileListResponse(total=len(all_files), files=all_files)


@router.get(
    "/{file_id}",
    response_model=FileInfoResponse,
    summary="Get File Information",
    description="Returns metadata and processing status for the specified file ID.",
)
@router.get(
    "/{file_id}/",
    response_model=FileInfoResponse,
    include_in_schema=False,
)
async def get_file_info(file_id: str):
    file_info = storage_service.get_file_info(file_id)
    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geospatial file with ID '{file_id}' not found.",
        )
    return file_info


@router.get(
    "/{file_id}/measurements",
    response_model=FileMeasurementsResponse,
    summary="Get Feature Measurements",
    description="Returns geometric measurements (area for polygons, length for linestrings) "
                "and projection metadata for all features in the specified file.",
)
@router.get(
    "/{file_id}/measurements/",
    response_model=FileMeasurementsResponse,
    include_in_schema=False,
)
async def get_measurements(file_id: str):
    measurements = storage_service.get_measurements(file_id)
    if not measurements:
        file_info = storage_service.get_file_info(file_id)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Geospatial file with ID '{file_id}' not found.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Measurements not available for file '{file_id}'. Processing status: {file_info.status}",
        )
    return measurements


@router.get(
    "/{file_id}/geojson",
    summary="Get GeoJSON Feature Collection",
    description="Returns the full GeoJSON FeatureCollection for mapping and visualization.",
)
@router.get(
    "/{file_id}/geojson/",
    include_in_schema=False,
)
async def get_geojson(file_id: str):
    geojson_data = storage_service.get_geojson_feature_collection(file_id)
    if not geojson_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geospatial features for file ID '{file_id}' not found.",
        )
    return JSONResponse(content=geojson_data)


@router.delete(
    "/{file_id}",
    summary="Delete File Record",
    description="Deletes file records and measurements from storage.",
)
@router.delete(
    "/{file_id}/",
    include_in_schema=False,
)
async def delete_file(file_id: str):
    success = storage_service.delete_file(file_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geospatial file with ID '{file_id}' not found.",
        )
    return {"message": f"File with ID '{file_id}' deleted successfully."}
