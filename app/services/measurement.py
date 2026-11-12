import logging
from typing import Optional
import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, Point, MultiPoint

from app.models.schemas import MeasurementInfo
from app.services.crs_manager import CRSManager

logger = logging.getLogger(__name__)

# WGS84 Ellipsoid for geodesic comparisons
_WGS84_GEOD = pyproj.Geod(ellps="WGS84")


class MeasurementService:
    """
    Calculates spatial measurements (Area for Polygons, Length for LineStrings)
    after reprojecting geometries from geographic coordinate systems into optimal
    metric projected systems (UTM). Gracefully handles points and unsupported types.
    """

    @classmethod
    def calculate_measurement(
        cls,
        geom: BaseGeometry,
        source_crs: pyproj.CRS,
    ) -> MeasurementInfo:
        """
        Computes the accurate measurement for a given Shapely geometry.
        """
        if geom is None or geom.is_empty:
            return MeasurementInfo(
                supported=False,
                measurement_type="none",
                primary_value=None,
                primary_unit=None,
                units={},
                note="Empty or null geometry; no measurement possible.",
            )

        geom_type = geom.geom_type

        # 1. Point / MultiPoint - Explicitly no measurement required
        if geom_type in ("Point", "MultiPoint"):
            return MeasurementInfo(
                supported=False,
                measurement_type="none",
                primary_value=None,
                primary_unit=None,
                units={},
                note="Point geometry represents a single location with zero area and zero length. No measurement required.",
            )

        # 2. Polygon / MultiPolygon - Area Calculation
        if geom_type in ("Polygon", "MultiPolygon"):
            try:
                # Reproject to metric projected coordinate system (UTM zone)
                proj_geom, proj_crs_code, proj_crs_name = CRSManager.reproject_for_measurement(geom, source_crs)
                area_m2 = float(proj_geom.area)
                perimeter_m = float(proj_geom.length)

                units = {
                    "sq_meters": round(area_m2, 2),
                    "sq_kilometers": round(area_m2 / 1_000_000.0, 6),
                    "hectares": round(area_m2 / 10_000.0, 4),
                    "acres": round(area_m2 * 0.000247105381, 4),
                    "sq_feet": round(area_m2 * 10.7639104, 2),
                    "perimeter_meters": round(perimeter_m, 2),
                    "perimeter_kilometers": round(perimeter_m / 1000.0, 4),
                }

                # Geodesic comparison if source was geographic WGS84
                geodesic = None
                if source_crs.is_geographic:
                    try:
                        geo_area, geo_perim = _WGS84_GEOD.geometry_area_perimeter(geom)
                        geodesic = {
                            "ellipsoidal_area_sq_meters": round(abs(geo_area), 2),
                            "ellipsoidal_perimeter_meters": round(abs(geo_perim), 2),
                        }
                    except Exception as ge:
                        logger.debug("Geodesic calculation skipped: %s", ge)

                return MeasurementInfo(
                    supported=True,
                    measurement_type="area",
                    primary_value=round(area_m2, 2),
                    primary_unit="sq_meters",
                    units=units,
                    projected_crs=proj_crs_code,
                    projected_crs_name=proj_crs_name,
                    geodesic_comparison=geodesic,
                    note=f"Projected into {proj_crs_code} ({proj_crs_name}) for accurate planar area calculation.",
                )
            except Exception as e:
                logger.error("Error calculating polygon area: %s", e, exc_info=True)
                return MeasurementInfo(
                    supported=False,
                    measurement_type="area",
                    primary_value=None,
                    primary_unit=None,
                    units={},
                    note=f"Measurement error: {str(e)}",
                )

        # 3. LineString / MultiLineString - Length Calculation
        if geom_type in ("LineString", "MultiLineString"):
            try:
                # Reproject to metric projected coordinate system (UTM zone)
                proj_geom, proj_crs_code, proj_crs_name = CRSManager.reproject_for_measurement(geom, source_crs)
                length_m = float(proj_geom.length)

                units = {
                    "meters": round(length_m, 2),
                    "kilometers": round(length_m / 1000.0, 4),
                    "feet": round(length_m * 3.2808399, 2),
                    "miles": round(length_m * 0.000621371192, 4),
                }

                # Geodesic comparison if source was geographic
                geodesic = None
                if source_crs.is_geographic:
                    try:
                        geo_len = _WGS84_GEOD.geometry_length(geom)
                        geodesic = {
                            "ellipsoidal_length_meters": round(abs(geo_len), 2),
                        }
                    except Exception as ge:
                        logger.debug("Geodesic calculation skipped: %s", ge)

                return MeasurementInfo(
                    supported=True,
                    measurement_type="length",
                    primary_value=round(length_m, 2),
                    primary_unit="meters",
                    units=units,
                    projected_crs=proj_crs_code,
                    projected_crs_name=proj_crs_name,
                    geodesic_comparison=geodesic,
                    note=f"Projected into {proj_crs_code} ({proj_crs_name}) for accurate planar distance calculation.",
                )
            except Exception as e:
                logger.error("Error calculating linestring length: %s", e, exc_info=True)
                return MeasurementInfo(
                    supported=False,
                    measurement_type="length",
                    primary_value=None,
                    primary_unit=None,
                    units={},
                    note=f"Measurement error: {str(e)}",
                )

        # 4. Graceful handling of unsupported geometry types (e.g. GeometryCollection)
        return MeasurementInfo(
            supported=False,
            measurement_type="unsupported",
            primary_value=None,
            primary_unit=None,
            units={},
            note=f"Geometry type '{geom_type}' is not supported for standard area or length calculation.",
        )

