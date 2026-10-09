"""
Pydantic Models for Feature Measurements and Statistical Summaries.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FeatureMeasurement(BaseModel):
    """Measurement result for an individual geospatial feature."""
    feature_id: str = Field(..., description="Feature identifier or sequential index")
    name: Optional[str] = Field(None, description="Feature name or label if available")
    geometry_type: str = Field(..., description="Geometry type (Polygon, LineString, Point, etc.)")
    original_crs: str = Field(..., description="CRS in which feature was provided")
    projected_crs: Optional[str] = Field(None, description="Projected CRS used for measurement calculations")
    
    # Polygon Measurements
    area_sq_m: Optional[float] = Field(None, description="Area in square meters (m²)")
    area_hectares: Optional[float] = Field(None, description="Area in hectares (ha)")
    area_sq_km: Optional[float] = Field(None, description="Area in square kilometers (km²)")
    perimeter_m: Optional[float] = Field(None, description="Perimeter in meters (m)")
    
    # LineString Measurements
    length_m: Optional[float] = Field(None, description="Length in meters (m)")
    length_km: Optional[float] = Field(None, description="Length in kilometers (km)")
    
    # Geodesic Ellipsoidal Cross-Verification
    geodesic_area_sq_m: Optional[float] = Field(None, description="Geodesic area calculated on WGS84 ellipsoid (m²)")
    geodesic_length_m: Optional[float] = Field(None, description="Geodesic length calculated on WGS84 ellipsoid (m)")
    
    # Geometry representation and attributes
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry representation")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Feature attributes/properties")
    
    # Status and diagnostics
    measurement_supported: bool = Field(True, description="Whether this geometry type supports length/area calculation")
    notes: Optional[str] = Field(None, description="Diagnostic notes, warnings, or explanation")


class MeasurementSummary(BaseModel):
    """Summary metrics across all features in the dataset."""
    total_features: int = Field(0, description="Total number of features")
    polygon_count: int = Field(0, description="Number of Polygon / MultiPolygon features")
    linestring_count: int = Field(0, description="Number of LineString / MultiLineString features")
    point_count: int = Field(0, description="Number of Point / MultiPoint features")
    unsupported_count: int = Field(0, description="Features with unsupported or empty geometry")
    
    # Aggregate Polygon Metrics
    total_area_sq_m: float = Field(0.0, description="Sum of all polygon areas in m²")
    total_area_hectares: float = Field(0.0, description="Sum of all polygon areas in hectares")
    total_area_sq_km: float = Field(0.0, description="Sum of all polygon areas in km²")
    
    # Aggregate LineString Metrics
    total_length_m: float = Field(0.0, description="Sum of all linestring lengths in m")
    total_length_km: float = Field(0.0, description="Sum of all linestring lengths in km")


class FileMeasurementsResponse(BaseModel):
    """
    Response for measurements endpoint:
    GET /api/files/{id}/measurements/
    """
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Uploaded file name")
    crs_original: str = Field(..., description="Original Coordinate Reference System")
    crs_projected_strategy: str = Field(
        ...,
        description="Strategy and projected coordinate systems utilized for metric measurements"
    )
    summary: MeasurementSummary = Field(..., description="Aggregate summary of measurements")
    measurements: List[FeatureMeasurement] = Field(..., description="Detailed list of per-feature measurements")
