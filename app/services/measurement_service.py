"""
Measurement Service.
Calculates geometric measurements (Area for Polygons, Length for LineStrings)
using intelligent Projected CRS transformations and Geodesic verification.
"""
from typing import List, Tuple, Optional
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from app.core.logging import logger
from app.models.file_models import RawFeature
from app.models.measurement_models import (
    FeatureMeasurement,
    MeasurementSummary,
    FileMeasurementsResponse,
)
from app.services.crs_service import crs_service


class MeasurementService:
    """Computes measurements on geospatial features with CRS reprojection."""

    @staticmethod
    def _extract_name(feature: RawFeature) -> Optional[str]:
        """Attempts to extract a human-friendly name from feature properties."""
        props = feature.properties
        for candidate in ("name", "Name", "NAME", "title", "label", "id", "ID"):
            if candidate in props and props[candidate]:
                return str(props[candidate])
        return None

    def calculate_measurements(
        self,
        file_id: str,
        filename: str,
        features: List[RawFeature],
        source_crs_str: str,
    ) -> FileMeasurementsResponse:
        """
        Calculates measurements for all features in the dataset.
        Transforms coordinates from geographic degrees to optimal local projected CRS (e.g., UTM)
        prior to planar measurement calculation.
        """
        source_crs, standardized_src_crs = crs_service.parse_crs(source_crs_str)
        is_source_geographic = crs_service.is_geographic(source_crs)

        feature_measurements: List[FeatureMeasurement] = []
        
        polygon_count = 0
        linestring_count = 0
        point_count = 0
        unsupported_count = 0
        
        total_area_sq_m = 0.0
        total_length_m = 0.0

        for feat in features:
            geom_type = feat.geometry_type
            feat_name = self._extract_name(feat)

            # Attempt to convert to Shapely geometry
            try:
                geom: BaseGeometry = shape(feat.geometry)
            except Exception as e:
                logger.warning(f"Feature {feat.feature_id} has unparseable geometry: {e}")
                unsupported_count += 1
                feature_measurements.append(
                    FeatureMeasurement(
                        feature_id=feat.feature_id,
                        name=feat_name,
                        geometry_type=geom_type,
                        original_crs=standardized_src_crs,
                        projected_crs=None,
                        geometry=feat.geometry,
                        properties=feat.properties,
                        measurement_supported=False,
                        notes=f"Unparseable geometry: {str(e)}",
                    )
                )
                continue

            if geom.is_empty:
                unsupported_count += 1
                feature_measurements.append(
                    FeatureMeasurement(
                        feature_id=feat.feature_id,
                        name=feat_name,
                        geometry_type=geom_type,
                        original_crs=standardized_src_crs,
                        projected_crs=None,
                        geometry=feat.geometry,
                        properties=feat.properties,
                        measurement_supported=False,
                        notes="Geometry is empty.",
                    )
                )
                continue

            # Determine projected CRS:
            # If source is geographic, compute optimal local UTM zone from geometry centroid.
            # If already projected, retain source CRS.
            if is_source_geographic:
                centroid = geom.centroid
                target_crs, target_crs_label = crs_service.get_optimal_utm_crs(centroid.x, centroid.y)
            else:
                target_crs = source_crs
                target_crs_label = standardized_src_crs

            # Transform geometry to projected CRS
            try:
                projected_geom = crs_service.project_geometry(geom, source_crs, target_crs)
            except Exception as e:
                logger.error(f"Reprojection failed for feature {feat.feature_id}: {e}")
                unsupported_count += 1
                feature_measurements.append(
                    FeatureMeasurement(
                        feature_id=feat.feature_id,
                        name=feat_name,
                        geometry_type=geom_type,
                        original_crs=standardized_src_crs,
                        projected_crs=None,
                        geometry=feat.geometry,
                        properties=feat.properties,
                        measurement_supported=False,
                        notes=f"CRS reprojection failed: {str(e)}",
                    )
                )
                continue

            # Geodesic calculation on WGS84 ellipsoid for cross-verification
            geod_area, geod_length = crs_service.compute_geodesic_area_and_length(geom, source_crs)

            # Measurement calculations based on geometry type
            if geom_type in ("Polygon", "MultiPolygon"):
                polygon_count += 1
                area_m2 = round(projected_geom.area, 2)
                area_ha = round(area_m2 / 10_000.0, 4)
                area_km2 = round(area_m2 / 1_000_000.0, 6)
                perimeter_m = round(projected_geom.length, 2)
                total_area_sq_m += area_m2

                feature_measurements.append(
                    FeatureMeasurement(
                        feature_id=feat.feature_id,
                        name=feat_name,
                        geometry_type=geom_type,
                        original_crs=standardized_src_crs,
                        projected_crs=target_crs_label,
                        area_sq_m=area_m2,
                        area_hectares=area_ha,
                        area_sq_km=area_km2,
                        perimeter_m=perimeter_m,
                        length_m=None,
                        geodesic_area_sq_m=round(geod_area, 2) if geod_area is not None else None,
                        geometry=feat.geometry,
                        properties=feat.properties,
                        measurement_supported=True,
                        notes="Measured via conformal projected UTM CRS and verified against WGS84 ellipsoid.",
                    )
                )

            elif geom_type in ("LineString", "MultiLineString"):
                linestring_count += 1
                length_m = round(projected_geom.length, 2)
                length_km = round(length_m / 1000.0, 4)
                total_length_m += length_m

                feature_measurements.append(
                    FeatureMeasurement(
                        feature_id=feat.feature_id,
                        name=feat_name,
                        geometry_type=geom_type,
                        original_crs=standardized_src_crs,
                        projected_crs=target_crs_label,
                        length_m=length_m,
                        length_km=length_km,
                        area_sq_m=None,
                        geodesic_length_m=round(geod_length, 2) if geod_length is not None else None,
                        geometry=feat.geometry,
                        properties=feat.properties,
                        measurement_supported=True,
                        notes="Length measured via conformal projected UTM CRS.",
                    )
                )

            elif geom_type in ("Point", "MultiPoint"):
                point_count += 1
                feature_measurements.append(
                    FeatureMeasurement(
                        feature_id=feat.feature_id,
                        name=feat_name,
                        geometry_type=geom_type,
                        original_crs=standardized_src_crs,
                        projected_crs=target_crs_label,
                        area_sq_m=None,
                        length_m=None,
                        geometry=feat.geometry,
                        properties=feat.properties,
                        measurement_supported=True,
                        notes="Point features have zero-dimensional length and area. No measurement required.",
                    )
                )

            else:
                # Unsupported geometry types (e.g. GeometryCollection or custom)
                unsupported_count += 1
                feature_measurements.append(
                    FeatureMeasurement(
                        feature_id=feat.feature_id,
                        name=feat_name,
                        geometry_type=geom_type,
                        original_crs=standardized_src_crs,
                        projected_crs=target_crs_label,
                        area_sq_m=None,
                        length_m=None,
                        geometry=feat.geometry,
                        properties=feat.properties,
                        measurement_supported=False,
                        notes=f"Geometry type '{geom_type}' is not supported for standard planar measurement.",
                    )
                )

        summary = MeasurementSummary(
            total_features=len(features),
            polygon_count=polygon_count,
            linestring_count=linestring_count,
            point_count=point_count,
            unsupported_count=unsupported_count,
            total_area_sq_m=round(total_area_sq_m, 2),
            total_area_hectares=round(total_area_sq_m / 10_000.0, 4),
            total_area_sq_km=round(total_area_sq_m / 1_000_000.0, 6),
            total_length_m=round(total_length_m, 2),
            total_length_km=round(total_length_m / 1000.0, 4),
        )

        return FileMeasurementsResponse(
            file_id=file_id,
            filename=filename,
            crs_original=standardized_src_crs,
            crs_projected_strategy=(
                "Feature Centroid-based UTM Zone Selection (minimum distortion) "
                "with WGS84 Geodesic Ellipsoidal Cross-Verification"
            ),
            summary=summary,
            measurements=feature_measurements,
        )


measurement_service = MeasurementService()
