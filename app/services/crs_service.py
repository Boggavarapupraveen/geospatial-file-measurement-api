"""
CRS (Coordinate Reference System) Service.
Handles CRS detection, classification, UTM zone selection, and coordinate reprojection.
"""
from typing import Tuple, Optional
import numpy as np
import pyproj
from pyproj import CRS, Transformer, Geod
from pyproj.exceptions import CRSError
from shapely.geometry.base import BaseGeometry
import shapely

from app.core.logging import logger
from app.core.exceptions import CRSTransformationException


class CRSService:
    """Service for managing coordinate reference systems, transformations, and projections."""

    def __init__(self):
        self.wgs84_geod = Geod(ellps="WGS84")

    @staticmethod
    def parse_crs(crs_input: str) -> Tuple[CRS, str]:
        """
        Parses a CRS input (EPSG code, WKT, PROJ string, or name) into a pyproj.CRS object.
        Returns a tuple of (CRS object, standardized CRS string).
        """
        if not crs_input or not crs_input.strip():
            logger.info("Empty CRS provided; defaulting to EPSG:4326")
            crs = CRS.from_epsg(4326)
            return crs, "EPSG:4326"

        crs_input_str = crs_input.strip()

        # Direct EPSG identifier check
        if crs_input_str.upper().startswith("EPSG:"):
            try:
                crs = CRS.from_user_input(crs_input_str)
                return crs, crs_input_str.upper()
            except CRSError:
                pass

        # Try parsing WKT or general user input
        try:
            crs = CRS.from_user_input(crs_input_str)
            epsg = crs.to_epsg()
            if epsg:
                return crs, f"EPSG:{epsg}"
            return crs, crs.name or "Custom CRS"
        except Exception as e:
            logger.warning(f"Could not parse CRS from '{crs_input_str[:50]}...': {e}. Falling back to EPSG:4326")
            return CRS.from_epsg(4326), "EPSG:4326"

    @staticmethod
    def is_geographic(crs: CRS) -> bool:
        """Determines if a CRS is geographic (uses angular degrees like latitude/longitude)."""
        return crs.is_geographic

    @staticmethod
    def get_optimal_utm_crs(lon: float, lat: float) -> Tuple[CRS, str]:
        """
        Calculates the optimal UTM (Universal Transverse Mercator) projected CRS
        for a given geographic coordinate (lon, lat in WGS84).
        
        UTM divides the Earth into 60 zones of 6 degrees longitude each,
        yielding minimum scale distortion (< 0.1%) within the zone.
        """
        # Clamp latitude to valid bounds for UTM [-80, 84]
        clamped_lat = max(-80.0, min(84.0, lat))
        
        # Calculate 6-degree UTM zone
        zone = int((lon + 180.0) / 6.0) + 1
        if zone > 60:
            zone = 60
        elif zone < 1:
            zone = 1

        is_north = clamped_lat >= 0
        epsg_code = (32600 + zone) if is_north else (32700 + zone)
        utm_crs = CRS.from_epsg(epsg_code)
        zone_str = f"EPSG:{epsg_code} (UTM Zone {zone}{'N' if is_north else 'S'})"
        return utm_crs, zone_str

    def project_geometry(
        self,
        geometry: BaseGeometry,
        source_crs: CRS,
        target_crs: CRS
    ) -> BaseGeometry:
        """
        Reprojects a Shapely geometry from source_crs to target_crs.
        Handles both 2D and 3D coordinate sequences.
        """
        if source_crs == target_crs:
            return geometry

        try:
            transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)

            def transform_coords(coords: np.ndarray) -> np.ndarray:
                if coords.shape[1] >= 3:
                    x, y, z = transformer.transform(coords[:, 0], coords[:, 1], coords[:, 2])
                    return np.column_stack([x, y, z])
                else:
                    x, y = transformer.transform(coords[:, 0], coords[:, 1])
                    return np.column_stack([x, y])

            return shapely.transform(geometry, transform_coords)
        except Exception as e:
            logger.error(f"Failed to reproject geometry: {e}")
            raise CRSTransformationException(f"Reprojection error: {str(e)}")

    def compute_geodesic_area_and_length(
        self,
        geometry: BaseGeometry,
        source_crs: CRS
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Computes the ellipsoidal geodesic area (m²) and length/perimeter (m) on the WGS84 ellipsoid.
        If source_crs is not WGS84 (EPSG:4326), geometry is first transformed to WGS84.
        """
        try:
            wgs84_crs = CRS.from_epsg(4326)
            geom_wgs84 = geometry
            if source_crs != wgs84_crs:
                geom_wgs84 = self.project_geometry(geometry, source_crs, wgs84_crs)

            geom_type = geom_wgs84.geom_type
            if geom_type in ("Polygon", "MultiPolygon"):
                # Geod geometry_area_perimeter returns (area, perimeter)
                area, perimeter = self.wgs84_geod.geometry_area_perimeter(geom_wgs84)
                return abs(area), abs(perimeter)
            elif geom_type in ("LineString", "MultiLineString"):
                length = self.wgs84_geod.geometry_length(geom_wgs84)
                return None, abs(length)
            else:
                return None, None
        except Exception as e:
            logger.warning(f"Geodesic computation failed for {geometry.geom_type}: {e}")
            return None, None


crs_service = CRSService()
