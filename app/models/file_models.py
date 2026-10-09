"""
Pydantic Models for Geospatial Files.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FileProcessingStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GeospatialFileType(str, Enum):
    SHAPEFILE_ZIP = "SHAPEFILE_ZIP"
    KML = "KML"
    UNKNOWN = "UNKNOWN"


class FileUploadResponse(BaseModel):
    """Response returned immediately upon uploading a file."""
    id: str = Field(..., description="Unique file identifier (UUID)")
    filename: str = Field(..., description="Original uploaded filename")
    file_type: str = Field(..., description="Detected file type (Shapefile or KML)")
    feature_count: int = Field(default=0, description="Number of geospatial features extracted")
    crs: str = Field(..., description="Coordinate Reference System of the file")
    status: FileProcessingStatus = Field(..., description="Processing status")
    uploaded_at: str = Field(..., description="Upload timestamp in ISO format")
    message: str = Field(default="File uploaded and processed successfully.")


class FileInfoResponse(BaseModel):
    """
    Response returned when requesting file information:
    GET /api/files/{id}/
    """
    id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Name of the uploaded geospatial file")
    file_type: Optional[str] = Field(None, description="Detected format (SHAPEFILE_ZIP or KML)")
    feature_count: int = Field(..., description="Total number of features in the file")
    crs: str = Field(..., description="Coordinate reference system (e.g., EPSG:4326)")
    status: str = Field(..., description="Status (COMPLETED, FAILED, PROCESSING)")
    uploaded_at: Optional[str] = Field(None, description="Upload timestamp")
    processed_at: Optional[str] = Field(None, description="Processing completion timestamp")
    file_size_bytes: Optional[int] = Field(None, description="Size of file in bytes")
    error: Optional[str] = Field(None, description="Error message if processing failed")


class FileListResponse(BaseModel):
    """Response for listing all uploaded files."""
    total: int
    files: List[FileInfoResponse]


class RawFeature(BaseModel):
    """Internal model for an extracted feature from Shapefile or KML."""
    feature_id: str
    geometry_type: str
    geometry: Dict[str, Any]  # GeoJSON dict
    crs: str
    properties: Dict[str, Any]
