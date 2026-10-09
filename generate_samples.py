"""
Utility to generate sample KML and zipped Shapefiles for testing and evaluation.
"""
import os
import zipfile
from pathlib import Path
import shapefile


def create_samples():
    samples_dir = Path("samples")
    samples_dir.mkdir(exist_ok=True)

    # 1. Sample KML
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>San Francisco Park &amp; Trails Survey</name>
    <Placemark>
      <name>Golden Gate Park Meadow</name>
      <description>Spacious recreation lawn</description>
      <ExtendedData>
        <Data name="zone_code"><value>REC-01</value></Data>
        <Data name="surface"><value>Grass</value></Data>
        <Data name="capacity"><value>5000</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -122.486,37.769,0 -122.478,37.769,0 -122.478,37.765,0 -122.486,37.765,0 -122.486,37.769,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
    <Placemark>
      <name>Panhandle Multi-use Trail</name>
      <description>Paved pedestrian and bike trail</description>
      <ExtendedData>
        <Data name="surface"><value>Asphalt</value></Data>
        <Data name="lighting"><value>Yes</value></Data>
      </ExtendedData>
      <LineString>
        <coordinates>
          -122.455,37.772,0 -122.448,37.772,0 -122.443,37.771,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Conservatory of Flowers</name>
      <description>Victorian greenhouse historic site</description>
      <Point>
        <coordinates>-122.460,37.772,0</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>"""

    kml_file = samples_dir / "san_francisco_park.kml"
    with open(kml_file, "w", encoding="utf-8") as f:
        f.write(kml_content)
    print(f"Created {kml_file}")

    # 2. Sample Shapefile (Polygons)
    temp_prefix = samples_dir / "temp_survey"
    w = shapefile.Writer(str(temp_prefix), shapeType=shapefile.POLYGON)
    w.field("id", "N")
    w.field("name", "C", size=50)
    w.field("land_use", "C", size=30)
    
    # Polygon 1: Civic Center Plaza
    w.poly([[[-122.420, 37.780], [-122.410, 37.780], [-122.410, 37.770], [-122.420, 37.770], [-122.420, 37.780]]])
    w.record(1, "Civic Center Plaza", "Municipal")
    
    # Polygon 2: Jefferson Square Park
    w.poly([[[-122.428, 37.779], [-122.423, 37.779], [-122.423, 37.776], [-122.428, 37.776], [-122.428, 37.779]]])
    w.record(2, "Jefferson Square Park", "Recreation")
    w.close()

    # Write PRJ
    wkt_wgs84 = (
        'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],'
        'PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
    )
    prj_file = samples_dir / "temp_survey.prj"
    with open(prj_file, "w", encoding="utf-8") as f:
        f.write(wkt_wgs84)

    # Zip Shapefile files
    zip_path = samples_dir / "california_survey.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for ext in (".shp", ".shx", ".dbf", ".prj"):
            fp = samples_dir / f"temp_survey{ext}"
            if fp.exists():
                zf.write(fp, arcname=f"california_survey{ext}")
                fp.unlink()
    print(f"Created {zip_path}")


if __name__ == "__main__":
    create_samples()
