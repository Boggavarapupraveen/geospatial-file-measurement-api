"""
Unit tests for Measurement Service.
"""
from shapely.geometry import Polygon, LineString, Point, mapping
from app.models.file_models import RawFeature
from app.services.measurement_service import measurement_service


def test_measurements_polygon_area_calculation():
    # Square polygon in San Francisco
    coords = [[-122.42, 37.78], [-122.41, 37.78], [-122.41, 37.77], [-122.42, 37.77], [-122.42, 37.78]]
    poly = Polygon(coords)

    feat = RawFeature(
        feature_id="poly_1",
        geometry_type="Polygon",
        geometry=mapping(poly),
        crs="EPSG:4326",
        properties={"name": "Mission District Park"},
    )

    resp = measurement_service.calculate_measurements(
        file_id="test_file_1",
        filename="sf_park.shp",
        features=[feat],
        source_crs_str="EPSG:4326",
    )

    assert resp.summary.total_features == 1
    assert resp.summary.polygon_count == 1
    assert resp.summary.total_area_sq_m > 0
    assert resp.summary.total_area_hectares > 0

    meas = resp.measurements[0]
    assert meas.area_sq_m is not None
    assert meas.area_hectares is not None
    assert meas.area_sq_km is not None
    assert meas.perimeter_m is not None
    assert meas.length_m is None
    assert "UTM Zone 10N" in meas.projected_crs
    assert meas.measurement_supported is True


def test_measurements_linestring_length_calculation():
    coords = [[-122.42, 37.78], [-122.41, 37.78], [-122.40, 37.78]]
    line = LineString(coords)

    feat = RawFeature(
        feature_id="line_1",
        geometry_type="LineString",
        geometry=mapping(line),
        crs="EPSG:4326",
        properties={"name": "Market Street Segment"},
    )

    resp = measurement_service.calculate_measurements(
        file_id="test_file_2",
        filename="streets.shp",
        features=[feat],
        source_crs_str="EPSG:4326",
    )

    assert resp.summary.linestring_count == 1
    assert resp.summary.total_length_m > 0
    meas = resp.measurements[0]
    assert meas.length_m is not None
    assert meas.length_km is not None
    assert meas.area_sq_m is None
    assert meas.measurement_supported is True


def test_measurements_point_gracefully_ignored():
    pt = Point(-122.42, 37.78)

    feat = RawFeature(
        feature_id="pt_1",
        geometry_type="Point",
        geometry=mapping(pt),
        crs="EPSG:4326",
        properties={"name": "Observation Tower"},
    )

    resp = measurement_service.calculate_measurements(
        file_id="test_file_3",
        filename="landmarks.kml",
        features=[feat],
        source_crs_str="EPSG:4326",
    )

    assert resp.summary.point_count == 1
    meas = resp.measurements[0]
    assert meas.area_sq_m is None
    assert meas.length_m is None
    assert meas.measurement_supported is True
    assert "No measurement required" in meas.notes


def test_measurements_unsupported_geometry_handled_gracefully():
    feat = RawFeature(
        feature_id="invalid_1",
        geometry_type="GeometryCollection",
        geometry={"type": "GeometryCollection", "geometries": []},
        crs="EPSG:4326",
        properties={},
    )

    resp = measurement_service.calculate_measurements(
        file_id="test_file_4",
        filename="odd_data.kml",
        features=[feat],
        source_crs_str="EPSG:4326",
    )

    assert resp.summary.unsupported_count == 1
    meas = resp.measurements[0]
    assert meas.measurement_supported is False
