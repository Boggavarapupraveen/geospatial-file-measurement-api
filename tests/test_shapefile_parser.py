"""
Unit tests for Shapefile Parser Service.
"""
import io
import tempfile
import zipfile
from pathlib import Path
import pytest

from app.core.exceptions import InvalidFileFormatException
from app.services.shapefile_parser import shapefile_parser


def test_parse_valid_shapefile_zip(sample_shapefile_zip_bytes):
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(sample_shapefile_zip_bytes)
        tmp_path = Path(tmp.name)

    try:
        features, crs_str = shapefile_parser.parse(tmp_path)
        assert len(features) == 1
        assert "4326" in crs_str

        feat = features[0]
        assert feat.geometry_type == "Polygon"
        assert feat.properties["name"] == "Civic Center Area"
        assert feat.properties["category"] == "Urban"
        assert feat.geometry["type"] == "Polygon"
    finally:
        tmp_path.unlink(missing_ok=True)


def test_parse_shapefile_zip_missing_shp():
    # Zip containing only a text file
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("readme.txt", "No shapefile here.")
    buffer.seek(0)

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(buffer.getvalue())
        tmp_path = Path(tmp.name)

    try:
        with pytest.raises(InvalidFileFormatException) as exc_info:
            shapefile_parser.parse(tmp_path)
        assert "does not contain any .shp" in str(exc_info.value)
    finally:
        tmp_path.unlink(missing_ok=True)


def test_parse_corrupted_zip():
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(b"NOT A REAL ZIP FILE CONTENT")
        tmp_path = Path(tmp.name)

    try:
        with pytest.raises(InvalidFileFormatException):
            shapefile_parser.parse(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
