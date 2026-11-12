import pyproj
from shapely.geometry import Polygon, LineString, Point, GeometryCollection

from app.services.measurement import MeasurementService

def test_polygon_area_calculation():
    src_crs = pyproj.CRS.from_epsg(4326)
    # Approx 375m x 444m rectangle
    poly = Polygon([
        (-122.335, 47.608),
        (-122.330, 47.608),
        (-122.330, 47.612),
        (-122.335, 47.612),
        (-122.335, 47.608),
    ])

    result = MeasurementService.calculate_measurement(poly, src_crs)
    assert result.supported is True
    assert result.measurement_type == "area"
    assert result.primary_unit == "sq_meters"
    assert result.primary_value > 100000
    assert "sq_meters" in result.units
    assert "hectares" in result.units
    assert "acres" in result.units
    assert "perimeter_meters" in result.units
    assert result.projected_crs == "EPSG:32610"

def test_linestring_length_calculation():
    src_crs = pyproj.CRS.from_epsg(4326)
    line = LineString([
        (-122.335, 47.608),
        (-122.330, 47.608),
    ])

    result = MeasurementService.calculate_measurement(line, src_crs)
    assert result.supported is True
    assert result.measurement_type == "length"
    assert result.primary_unit == "meters"
    # Approx 375 meters
    assert 300 < result.primary_value < 450
    assert "meters" in result.units
    assert "kilometers" in result.units
    assert "miles" in result.units
    assert result.projected_crs == "EPSG:32610"

def test_point_no_measurement_required():
    src_crs = pyproj.CRS.from_epsg(4326)
    point = Point(-122.332, 47.610)

    result = MeasurementService.calculate_measurement(point, src_crs)
    assert result.supported is False
    assert result.measurement_type == "none"
    assert result.primary_value is None
    assert "No measurement required" in result.note

def test_unsupported_geometry_handled_gracefully():
    src_crs = pyproj.CRS.from_epsg(4326)
    geom_col = GeometryCollection([Point(0, 0), LineString([(0, 0), (1, 1)])])

    result = MeasurementService.calculate_measurement(geom_col, src_crs)
    assert result.supported is False
    assert result.measurement_type == "unsupported"
    assert result.primary_value is None
    assert "not supported" in result.note

