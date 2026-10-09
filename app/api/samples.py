"""
Sample Data Generator and Endpoint.
Provides downloadable sample Shapefiles and KML for rapid testing and demonstrations.
"""
import io
import os
import tempfile
import zipfile
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import Response
import shapefile

router = APIRouter(prefix="/samples", tags=["Samples"])


def generate_sample_shapefile_zip_bytes() -> bytes:
    """Generates an in-memory zip file containing an ESRI Shapefile with Polygon, LineString, and Point records."""
    buffer = io.BytesIO()

    with tempfile.TemporaryDirectory() as td:
        base_name = "survey_polygons"
        shp_path = os.path.join(td, f"{base_name}.shp")
        prj_path = os.path.join(td, f"{base_name}.prj")

        # Create Shapefile with polygons
        w = shapefile.Writer(shp_path, shapeType=shapefile.POLYGON)
        w.field("id", "N")
        w.field("name", "C", size=50)
        w.field("zone_type", "C", size=30)

        # Polygon 1: Central Park Section
        w.poly([
            [[-73.97, 40.78], [-73.96, 40.78], [-73.96, 40.77], [-73.97, 40.77], [-73.97, 40.78]]
        ])
        w.record(1, "Central Meadow", "Recreational")

        # Polygon 2: Reservoir Area
        w.poly([
            [[-73.965, 40.785], [-73.958, 40.785], [-73.958, 40.781], [-73.965, 40.781], [-73.965, 40.785]]
        ])
        w.record(2, "Jacqueline Reservoir", "Waterbody")

        w.close()

        # Write WGS 84 PRJ
        wkt_wgs84 = (
            'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137,298.257223563]],'
            'PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]]'
        )
        with open(prj_path, "w", encoding="utf-8") as f:
            f.write(wkt_wgs84)

        # Bundle into zip
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                file_on_disk = os.path.join(td, f"{base_name}{ext}")
                if os.path.exists(file_on_disk):
                    zf.write(file_on_disk, arcname=f"{base_name}{ext}")

    buffer.seek(0)
    return buffer.getvalue()


@router.get("/shapefile", summary="Download Sample Shapefile (.zip)")
async def get_sample_shapefile():
    """Generates and returns a valid sample Shapefile zip archive for instant testing."""
    zip_bytes = generate_sample_shapefile_zip_bytes()
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="sample_survey_shapefile.zip"'},
    )
