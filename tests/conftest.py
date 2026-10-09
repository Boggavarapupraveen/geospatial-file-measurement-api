"""
Pytest configuration and shared fixtures.
"""
import io
import os
import tempfile
import zipfile
import pytest
from fastapi.testclient import TestClient
import shapefile

from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def sample_kml_content() -> str:
    """Sample valid KML string with Polygon, LineString, and Point."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Presidio Park Survey</name>
    <Placemark id="p1">
      <name>Main Botanical Garden</name>
      <description>Presidio Botanical Park Section A</description>
      <ExtendedData>
        <Data name="zone"><value>Park_A</value></Data>
        <Data name="capacity"><value>1200</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -122.460,37.790,0 -122.455,37.790,0 -122.455,37.785,0 -122.460,37.785,0 -122.460,37.790,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark id="l1">
      <name>Coastal Scenic Trail</name>
      <description>North coastal hiking path</description>
      <LineString>
        <coordinates>
          -122.465,37.792,0 -122.460,37.795,0 -122.455,37.793,0 -122.450,37.796,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark id="pt1">
      <name>Overlook Point</name>
      <description>Panoramic viewpoint</description>
      <Point>
        <coordinates>-122.458,37.792,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>"""


@pytest.fixture
def sample_kml_bytes(sample_kml_content) -> bytes:
    return sample_kml_content.encode("utf-8")


@pytest.fixture
def sample_shapefile_zip_bytes() -> bytes:
    """Creates an in-memory zip file of a shapefile containing Polygon, LineString, and Point records."""
    buffer = io.BytesIO()
    with tempfile.TemporaryDirectory() as td:
        base_name = "test_features"
        shp_path = os.path.join(td, f"{base_name}.shp")
        prj_path = os.path.join(td, f"{base_name}.prj")

        # Write polygon shapefile
        w = shapefile.Writer(shp_path, shapeType=shapefile.POLYGON)
        w.field("name", "C", size=50)
        w.field("category", "C", size=30)

        # Polygon 1: ~ 0.01 deg x 0.01 deg square in SF (~ 1 km x ~ 0.8 km)
        w.poly([
            [[-122.42, 37.78], [-122.41, 37.78], [-122.41, 37.77], [-122.42, 37.77], [-122.42, 37.78]]
        ])
        w.record("Civic Center Area", "Urban")

        w.close()

        # WGS 84 PRJ
        wkt_wgs84 = (
            'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],'
            'PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'
        )
        with open(prj_path, "w", encoding="utf-8") as f:
            f.write(wkt_wgs84)

        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                fpath = os.path.join(td, f"{base_name}{ext}")
                if os.path.exists(fpath):
                    zf.write(fpath, arcname=f"{base_name}{ext}")

    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def sample_linestring_shapefile_zip_bytes() -> bytes:
    """Creates a shapefile zip with LineStrings."""
    buffer = io.BytesIO()
    with tempfile.TemporaryDirectory() as td:
        base_name = "test_roads"
        shp_path = os.path.join(td, f"{base_name}.shp")
        prj_path = os.path.join(td, f"{base_name}.prj")

        w = shapefile.Writer(shp_path, shapeType=shapefile.POLYLINE)
        w.field("road_name", "C", size=50)
        w.line([[[-122.40, 37.78], [-122.39, 37.78], [-122.38, 37.79]]])
        w.record("Market Street")
        w.close()

        wkt_wgs84 = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
        with open(prj_path, "w", encoding="utf-8") as f:
            f.write(wkt_wgs84)

        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                fpath = os.path.join(td, f"{base_name}{ext}")
                if os.path.exists(fpath):
                    zf.write(fpath, arcname=f"{base_name}{ext}")

    buffer.seek(0)
    return buffer.getvalue()
