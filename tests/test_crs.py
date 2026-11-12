import pyproj
from shapely.geometry import Polygon, LineString

from app.services.crs_manager import CRSManager

def test_parse_crs_valid_epsg():
    crs, name = CRSManager.parse_crs("EPSG:4326")
    assert crs.is_geographic is True
    assert "4326" in name

def test_parse_crs_invalid_fallback():
    crs, name = CRSManager.parse_crs("INVALID_CRS_STRING_123")
    assert crs.is_geographic is True
    assert name == "EPSG:4326"

def test_get_optimal_utm_epsg_northern_hemisphere():
    # Longitude -122.33 (Seattle, WA), Latitude 47.60 -> Zone 10 North
    # Zone = int((-122.33 + 180) / 6) + 1 = 10 -> EPSG:32610
    epsg, name = CRSManager.get_optimal_utm_epsg(-122.33, 47.60)
    assert epsg == 32610
    assert "zone 10N" in name

def test_get_optimal_utm_epsg_southern_hemisphere():
    # Longitude 151.20 (Sydney, Australia), Latitude -33.86 -> Zone 56 South
    # Zone = int((151.20 + 180) / 6) + 1 = 56 -> EPSG:32756
    epsg, name = CRSManager.get_optimal_utm_epsg(151.20, -33.86)
    assert epsg == 32756
    assert "zone 56S" in name

def test_reproject_for_measurement_changes_units():
    # 0.001 x 0.001 degree square in Seattle (~75m x 111m)
    poly_deg = Polygon([
        (-122.335, 47.608),
        (-122.330, 47.608),
        (-122.330, 47.612),
        (-122.335, 47.612),
        (-122.335, 47.608),
    ])
    src_crs = pyproj.CRS.from_epsg(4326)

    proj_geom, crs_code, crs_name = CRSManager.reproject_for_measurement(poly_deg, src_crs)
    assert crs_code == "EPSG:32610"
    
    # In degrees, poly_deg.area is ~ 0.005 * 0.004 = 0.00002 sq degrees
    assert poly_deg.area < 0.001
    
    # In projected UTM meters, proj_geom.area should be roughly ~160,000 m²
    assert proj_geom.area > 50000
    assert proj_geom.area < 500000
