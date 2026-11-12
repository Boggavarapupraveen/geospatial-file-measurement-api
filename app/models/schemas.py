from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class MeasurementInfo(BaseModel):
    supported: bool = Field(..., description="Whether this geometry type supports measurements")
    measurement_type: Optional[str] = Field(None, description="'area', 'length', or 'none'")
    primary_value: Optional[float] = Field(None, description="Primary measurement value in SI units (m² or m)")
    primary_unit: Optional[str] = Field(None, description="Unit of primary value ('sq_meters' or 'meters')")
    units: Dict[str, float] = Field(default_factory=dict, description="Calculated values in multiple standard units")
    projected_crs: Optional[str] = Field(None, description="Projected CRS code used for planar measurement")
    projected_crs_name: Optional[str] = Field(None, description="Name of the projected coordinate reference system")
    geodesic_comparison: Optional[Dict[str, float]] = Field(None, description="Direct WGS84 ellipsoidal measurement")
    note: Optional[str] = Field(None, description="Additional context or notes regarding measurement")


class FeatureDetail(BaseModel):
    id: Union[int, str] = Field(..., description="Feature identifier or index")
    geometry_type: str = Field(..., description="Type of geometry (e.g. Polygon, LineString, Point)")
    crs: str = Field(..., description="Coordinate Reference System of the source feature")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry object")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Feature attributes and metadata")
    measurement: MeasurementInfo = Field(..., description="Measurement results and CRS transformation info")


class FileInfo(BaseModel):
    id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="Detected format (SHAPEFILE_ZIP or KML)")
    feature_count: int = Field(..., description="Total number of extracted features")
    crs: str = Field(..., description="Detected CRS of the dataset")
    status: str = Field(..., description="Processing status: COMPLETED, FAILED, or PROCESSING")
    geometry_summary: Dict[str, int] = Field(default_factory=dict, description="Counts of each geometry type")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class FileDetailResponse(FileInfo):
    features: List[FeatureDetail] = Field(default_factory=list, description="Extracted features with measurements")


class FileListResponse(BaseModel):
    total: int
    files: List[FileInfo]


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    id: Union[int, str]
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    name: Optional[str] = None
    crs: Optional[Dict[str, Any]] = None
    features: List[GeoJSONFeature]

