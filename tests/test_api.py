import io
import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.api.files import (
    delete_file,
    get_feature_by_id,
    get_features,
    get_file_details,
    get_file_info,
    get_geojson,
    list_files,
    upload_file,
)
from app.config import SAMPLES_DIR

@pytest.fixture
def kml_upload_file():
    kml_bytes = (SAMPLES_DIR / "sample_survey.kml").read_bytes()
    return UploadFile(filename="survey.kml", file=io.BytesIO(kml_bytes))

@pytest.fixture
def shapefile_upload_file():
    shp_bytes = (SAMPLES_DIR / "sample_shapefile.zip").read_bytes()
    return UploadFile(filename="cadastral.zip", file=io.BytesIO(shp_bytes))

def test_upload_kml_api(kml_upload_file):
    res = upload_file(file=kml_upload_file)
    assert res.id is not None
    assert res.filename == "survey.kml"
    assert res.file_type == "KML"
    assert res.feature_count == 3
    assert "4326" in res.crs
    assert res.status == "COMPLETED"

    # Verify GET /api/files/{id}/
    info = get_file_info(res.id)
    assert info.id == res.id
    assert info.filename == "survey.kml"
    assert info.feature_count == 3
    assert info.status == "COMPLETED"

def test_upload_shapefile_api(shapefile_upload_file):
    res = upload_file(file=shapefile_upload_file)
    assert res.id is not None
    assert res.filename == "cadastral.zip"
    assert res.file_type == "SHAPEFILE_ZIP"
    assert res.feature_count == 2
    assert res.status == "COMPLETED"

def test_upload_invalid_extension():
    bad_file = UploadFile(filename="script.sh", file=io.BytesIO(b"echo hello"))
    with pytest.raises(HTTPException) as exc:
        upload_file(file=bad_file)
    assert exc.value.status_code == 400
    assert "Unsupported file extension" in exc.value.detail

def test_get_features_and_measurements(kml_upload_file):
    up = upload_file(file=kml_upload_file)
    features = get_features(up.id)
    assert len(features) == 3

    # 1. Polygon -> Area
    poly = next(f for f in features if f.geometry_type == "Polygon")
    assert poly.measurement.supported is True
    assert poly.measurement.measurement_type == "area"
    assert poly.measurement.primary_unit == "sq_meters"
    assert poly.measurement.primary_value > 0
    assert "hectares" in poly.measurement.units
    assert "acres" in poly.measurement.units

    # 2. LineString -> Length
    line = next(f for f in features if f.geometry_type == "LineString")
    assert line.measurement.supported is True
    assert line.measurement.measurement_type == "length"
    assert line.measurement.primary_unit == "meters"
    assert line.measurement.primary_value > 0
    assert "kilometers" in line.measurement.units

    # 3. Point -> No measurement required
    pt = next(f for f in features if f.geometry_type == "Point")
    assert pt.measurement.supported is False
    assert pt.measurement.measurement_type == "none"
    assert pt.measurement.primary_value is None

def test_get_geojson_feature_collection(kml_upload_file):
    up = upload_file(file=kml_upload_file)
    geojson = get_geojson(up.id)
    assert geojson.type == "FeatureCollection"
    assert len(geojson.features) == 3
    for f in geojson.features:
        assert f.geometry["type"] in ("Polygon", "LineString", "Point")
        assert "_measurement" in f.properties

def test_get_nonexistent_file():
    with pytest.raises(HTTPException) as exc:
        get_file_info("non_existent_id")
    assert exc.value.status_code == 404

def test_delete_file_api(kml_upload_file):
    up = upload_file(file=kml_upload_file)
    file_id = up.id

    del_res = delete_file(file_id)
    assert "successfully deleted" in del_res["message"]

    with pytest.raises(HTTPException) as exc:
        get_file_info(file_id)
    assert exc.value.status_code == 404

def test_list_files_api(kml_upload_file):
    upload_file(file=kml_upload_file)
    file_list = list_files()
    assert file_list.total >= 1
    assert any(f.filename == "survey.kml" for f in file_list.files)
