from pathlib import Path
from app.config import SAMPLES_DIR
from app.services.kml_parser import KMLParser
from app.services.shapefile_parser import ShapefileParser

def test_kml_parser_reads_features():
    kml_file = SAMPLES_DIR / "sample_survey.kml"
    features, crs, crs_name = KMLParser.parse_file(kml_file)

    assert len(features) == 3
    assert crs.is_geographic is True
    assert "4326" in crs_name

    geom_types = [f["geom_type"] for f in features]
    assert "Polygon" in geom_types
    assert "LineString" in geom_types
    assert "Point" in geom_types

    # Verify attributes extracted
    polygon_feat = [f for f in features if f["geom_type"] == "Polygon"][0]
    assert polygon_feat["properties"]["name"] == "Emerald Lake"
    assert polygon_feat["properties"].get("depth_meters") == "8.5"

def test_shapefile_parser_reads_zipped_features():
    shp_zip = SAMPLES_DIR / "sample_shapefile.zip"
    features, crs, crs_name = ShapefileParser.parse_zip(shp_zip)

    assert len(features) == 2
    assert "4326" in crs_name
    for f in features:
        assert f["geom_type"] == "Polygon"
        assert "Commercial District Alpha" in f["properties"].get("NAME", "") or "Greenwood Residential" in f["properties"].get("NAME", "")
