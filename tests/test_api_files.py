"""
Integration tests for FastAPI endpoints:
- POST /api/files/
- GET /api/files/{id}/
- GET /api/files/{id}/measurements/
- GET /api/files/{id}/geojson/
- GET /api/files/
- DELETE /api/files/{id}/
- GET /api/health
"""
import io
import pytest


def test_health_check_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "version" in data


def test_upload_kml_file(client, sample_kml_bytes):
    files = {"file": ("presidio.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    response = client.post("/api/files/", files=files)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["filename"] == "presidio.kml"
    assert data["file_type"] == "KML"
    assert data["feature_count"] == 3
    assert data["crs"] == "EPSG:4326"
    assert data["status"] == "COMPLETED"

    file_id = data["id"]

    # 1. Test GET /api/files/{id}/
    info_resp = client.get(f"/api/files/{file_id}/")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert info_data["id"] == file_id
    assert info_data["filename"] == "presidio.kml"
    assert info_data["feature_count"] == 3
    assert info_data["status"] == "COMPLETED"

    # 2. Test GET /api/files/{id}/measurements/
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert meas_data["file_id"] == file_id
    assert meas_data["summary"]["total_features"] == 3
    assert meas_data["summary"]["polygon_count"] == 1
    assert meas_data["summary"]["linestring_count"] == 1
    assert meas_data["summary"]["point_count"] == 1
    assert meas_data["summary"]["total_area_sq_m"] > 0
    assert meas_data["summary"]["total_length_m"] > 0

    # 3. Test GET /api/files/{id}/geojson/
    geo_resp = client.get(f"/api/files/{file_id}/geojson/")
    assert geo_resp.status_code == 200
    geo_data = geo_resp.json()
    assert geo_data["type"] == "FeatureCollection"
    assert len(geo_data["features"]) == 3


def test_upload_shapefile_zip(client, sample_shapefile_zip_bytes):
    files = {"file": ("civic_center.zip", sample_shapefile_zip_bytes, "application/zip")}
    response = client.post("/api/files/", files=files)
    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["filename"] == "civic_center.zip"
    assert data["file_type"] == "SHAPEFILE_ZIP"
    assert data["feature_count"] == 1
    assert data["status"] == "COMPLETED"

    file_id = data["id"]

    # Test measurements
    meas_resp = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_resp.status_code == 200
    meas_data = meas_resp.json()
    assert meas_data["summary"]["polygon_count"] == 1
    assert meas_data["summary"]["total_area_sq_m"] > 0


def test_upload_invalid_file_extension(client):
    files = {"file": ("data.txt", b"Hello world", "text/plain")}
    response = client.post("/api/files/", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_get_nonexistent_file(client):
    response = client.get("/api/files/non-existent-uuid-12345/")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_delete_file(client, sample_kml_bytes):
    files = {"file": ("to_delete.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    upload_res = client.post("/api/files/", files=files)
    file_id = upload_res.json()["id"]

    # Delete
    del_res = client.delete(f"/api/files/{file_id}/")
    assert del_res.status_code == 200

    # Verify 404 after deletion
    get_res = client.get(f"/api/files/{file_id}/")
    assert get_res.status_code == 404


def test_list_files(client, sample_kml_bytes):
    files = {"file": ("list_test.kml", sample_kml_bytes, "application/vnd.google-earth.kml+xml")}
    client.post("/api/files/", files=files)

    list_res = client.get("/api/files/")
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 1
    assert len(data["files"]) >= 1
