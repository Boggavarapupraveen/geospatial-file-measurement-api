"""
Unit tests for CRSService.
"""
import pytest
from shapely.geometry import Polygon, LineString, Point
from pyproj import CRS

from app.services.crs_service import crs_service


def test_parse_crs_standard_epsg():
    crs, label = crs_service.parse_crs("EPSG:4326")
    assert label == "EPSG:4326"
    assert crs.to_epsg() == 4326


def test_parse_crs_wkt_wgs84():
    wkt = (
        'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
        'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
    )
    crs, label = crs_service.parse_crs(wkt)
    assert crs.to_epsg() == 4326
    assert "EPSG:4326" in label


def test_parse_crs_fallback_on_invalid():
    crs, label = crs_service.parse_crs("NOT_A_VALID_CRS_STRING_12345")
    assert label == "EPSG:4326"
    assert crs.to_epsg() == 4326


def test_is_geographic():
    wgs84 = CRS.from_epsg(4326)
    utm33n = CRS.from_epsg(32633)
    web_mercator = CRS.from_epsg(3857)

    assert crs_service.is_geographic(wgs84) is True
    assert crs_service.is_geographic(utm33n) is False
    assert crs_service.is_geographic(web_mercator) is False


def test_get_optimal_utm_crs_california():
    # San Francisco (~ -122.4, 37.7) -> UTM Zone 10N (EPSG:32610)
    crs, label = crs_service.get_optimal_utm_crs(-122.4, 37.7)
    assert crs.to_epsg() == 32610
    assert "Zone 10N" in label


def test_get_optimal_utm_crs_southern_hemisphere():
    # Sydney, Australia (~ 151.2, -33.8) -> UTM Zone 56S (EPSG:32756)
    crs, label = crs_service.get_optimal_utm_crs(151.2, -33.8)
    assert crs.to_epsg() == 32756
    assert "Zone 56S" in label


def test_project_geometry_polygon():
    # Square in Copenhagen: (12.5, 55.6)
    poly = Polygon([(12.5, 55.6), (12.6, 55.6), (12.6, 55.7), (12.5, 55.7), (12.5, 55.6)])
    src_crs = CRS.from_epsg(4326)
    target_crs = CRS.from_epsg(32633)  # UTM 33N

    projected_poly = crs_service.project_geometry(poly, src_crs, target_crs)
    assert projected_poly.geom_type == "Polygon"
    assert projected_poly.area > 0
    # Area of ~0.1 deg square at latitude 55.6 is ~70-75 million sq meters
    assert 60_000_000 < projected_poly.area < 80_000_000


def test_compute_geodesic_area_and_length():
    poly = Polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)])
    src_crs = CRS.from_epsg(4326)
    area, perimeter = crs_service.compute_geodesic_area_and_length(poly, src_crs)

    assert area is not None
    # 1 deg x 1 deg at equator is ~111km x 111km ~= 1.23e10 m²
    assert 1.2e10 < area < 1.3e10
    assert perimeter is not None
    assert perimeter > 400_000
