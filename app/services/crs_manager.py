import logging
from typing import Optional, Tuple
import numpy as np
import pyproj
import shapely
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)

# Fallback / standard geographic CRS
DEFAULT_GEOGRAPHIC_CRS = "EPSG:4326"


class CRSManager:
    """
    Manages Coordinate Reference System detection, validation,
    and automatic metric reprojection for accurate geospatial measurements.
    """

    @staticmethod
    def parse_crs(crs_input: Optional[str]) -> Tuple[pyproj.CRS, str]:
        """
        Parses a CRS from EPSG code, Proj4 string, or WKT string.
        Falls back safely to EPSG:4326 if unparseable.
        """
        if not crs_input or not crs_input.strip():
            return pyproj.CRS.from_epsg(4326), DEFAULT_GEOGRAPHIC_CRS

        crs_str = crs_input.strip()
        try:
            crs_obj = pyproj.CRS.from_user_input(crs_str)
            # Standardize authority name if available (e.g. EPSG:4326)
            auth_name = crs_obj.to_authority()
            readable = f"{auth_name[0]}:{auth_name[1]}" if auth_name else crs_obj.name
            return crs_obj, readable
        except Exception as e:
            logger.warning("Failed to parse CRS '%s': %s. Falling back to %s", crs_str[:50], e, DEFAULT_GEOGRAPHIC_CRS)
            return pyproj.CRS.from_epsg(4326), DEFAULT_GEOGRAPHIC_CRS

    @staticmethod
    def get_optimal_utm_epsg(lon: float, lat: float) -> Tuple[int, str]:
        """
        Determines the optimal UTM projection EPSG code for a given longitude and latitude.
        - Longitude determines UTM Zone (1 to 60)
        - Latitude determines Northern (326xx) or Southern (327xx) hemisphere
        - Polar latitudes (|lat| > 84) use Universal Polar Stereographic (32661 / 32761)
        """
        # Polar bounds check
        if lat > 84.0:
            return 32661, "UPS North (Universal Polar Stereographic)"
        if lat < -80.0:
            return 32761, "UPS South (Universal Polar Stereographic)"

        # Normal UTM zone calculation (6 degrees per zone)
        zone = int((lon + 180.0) / 6.0) + 1
        zone = max(1, min(60, zone))

        if lat >= 0:
            epsg = 32600 + zone
            name = f"WGS 84 / UTM zone {zone}N"
        else:
            epsg = 32700 + zone
            name = f"WGS 84 / UTM zone {zone}S"

        return epsg, name

    @classmethod
    def reproject_for_measurement(
        cls,
        geom: BaseGeometry,
        source_crs: pyproj.CRS,
    ) -> Tuple[BaseGeometry, str, str]:
        """
        Transforms a geometry into an appropriate metric projected coordinate system
        so that Euclidean distance and area calculations are physically meaningful in meters.

        Returns:
            (projected_geom, target_crs_code, target_crs_name)
        """
        if geom.is_empty:
            return geom, "EPSG:4326", "Empty Geometry"

        # If source is already projected in meters, no reprojection is needed
        if source_crs.is_projected:
            # Check linear units
            axis_info = source_crs.axis_info
            is_meters = any("metre" in str(getattr(ax, "unit_name", "")).lower() for ax in axis_info)
            if is_meters:
                auth = source_crs.to_authority()
                code = f"{auth[0]}:{auth[1]}" if auth else "Projected"
                return geom, code, source_crs.name

        # Calculate representative point (lon, lat) for selecting the projection zone
        centroid = geom.centroid
        lon, lat = centroid.x, centroid.y

        # If source is geographic, ensure coordinates are lon, lat
        target_epsg, target_name = cls.get_optimal_utm_epsg(lon, lat)
        target_crs = pyproj.CRS.from_epsg(target_epsg)

        # PyProj Transformer with always_xy=True ensures (x=lon, y=lat) order
        transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)

        def transform_coords(coords: np.ndarray) -> np.ndarray:
            x, y = transformer.transform(coords[:, 0], coords[:, 1])
            if coords.shape[1] >= 3:
                return np.column_stack([x, y, coords[:, 2]])
            return np.column_stack([x, y])

        projected_geom = shapely.transform(geom, transform_coords)
        return projected_geom, f"EPSG:{target_epsg}", target_name
