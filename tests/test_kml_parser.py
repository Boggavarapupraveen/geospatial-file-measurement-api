"""
Unit tests for KML Parser Service.
"""
import tempfile
from pathlib import Path
import pytest

from app.core.exceptions import InvalidFileFormatException
from app.services.kml_parser import kml_parser


def test_parse_valid_kml(sample_kml_content):
    with tempfile.NamedTemporaryFile(suffix=".kml", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(sample_kml_content)
        tmp_path = Path(tmp.name)

    try:
        features, crs_str = kml_parser.parse(tmp_path)
        assert crs_str == "EPSG:4326"
        assert len(features) == 3

        # Verify Polygon feature
        poly_feat = next(f for f in features if f.geometry_type == "Polygon")
        assert poly_feat.properties["name"] == "Main Botanical Garden"
        assert poly_feat.properties["zone"] == "Park_A"
        assert poly_feat.properties["capacity"] == "1200"
        assert poly_feat.geometry["type"] == "Polygon"

        # Verify LineString feature
        line_feat = next(f for f in features if f.geometry_type == "LineString")
        assert line_feat.properties["name"] == "Coastal Scenic Trail"
        assert line_feat.geometry["type"] == "LineString"

        # Verify Point feature
        pt_feat = next(f for f in features if f.geometry_type == "Point")
        assert pt_feat.properties["name"] == "Overlook Point"
        assert pt_feat.geometry["type"] == "Point"

    finally:
        tmp_path.unlink(missing_ok=True)


def test_parse_malformed_xml():
    with tempfile.NamedTemporaryFile(suffix=".kml", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write("<kml><unclosed_tag>")
        tmp_path = Path(tmp.name)

    try:
        with pytest.raises(InvalidFileFormatException):
            kml_parser.parse(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def test_parse_empty_placemarks():
    empty_kml = """<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Document></Document>
    </kml>"""
    with tempfile.NamedTemporaryFile(suffix=".kml", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(empty_kml)
        tmp_path = Path(tmp.name)

    try:
        features, crs_str = kml_parser.parse(tmp_path)
        assert features == []
        assert crs_str == "EPSG:4326"
    finally:
        tmp_path.unlink(missing_ok=True)
