from pathlib import Path
import tempfile
import zipfile
import shapefile

def generate_samples(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate Sample KML
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Metropolitan Park Geospatial Survey</name>
    <description>Ground survey containing park boundary, fitness loop trail, and visitor landmarks.</description>
    
    <!-- Polygon: Lake / Reservoir -->
    <Placemark id="feat-lake-01">
      <name>Emerald Lake</name>
      <description>Artificial recreational lake within park grounds.</description>
      <ExtendedData>
        <Data name="category"><value>Water Body</value></Data>
        <Data name="depth_meters"><value>8.5</value></Data>
        <Data name="maintenance"><value>City Parks Dept</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -122.335,47.608,0
              -122.330,47.608,0
              -122.330,47.612,0
              -122.335,47.612,0
              -122.335,47.608,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>

    <!-- LineString: Walking Trail -->
    <Placemark id="feat-trail-01">
      <name>Pine Ridge Walking Trail</name>
      <description>Paved multi-use trail looping along the eastern perimeter.</description>
      <ExtendedData>
        <Data name="surface"><value>Asphalt</value></Data>
        <Data name="difficulty"><value>Easy</value></Data>
      </ExtendedData>
      <LineString>
        <coordinates>
          -122.335,47.608,0
          -122.328,47.609,0
          -122.327,47.613,0
          -122.331,47.615,0
        </coordinates>
      </LineString>
    </Placemark>

    <!-- Point: Visitor Center Landmark -->
    <Placemark id="feat-landmark-01">
      <name>Visitor Information Center</name>
      <description>Park headquarters, restrooms, and emergency station.</description>
      <ExtendedData>
        <Data name="facility_type"><value>Office</value></Data>
        <Data name="open_hours"><value>08:00 - 18:00</value></Data>
      </ExtendedData>
      <Point>
        <coordinates>-122.332,47.610,15</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>
"""
    kml_path = output_dir / "sample_survey.kml"
    kml_path.write_text(kml_content, encoding="utf-8")
    
    # 2. Generate Sample Shapefile and zip it
    temp_shp_dir = Path(tempfile.mkdtemp(prefix="sample_shp_"))
    try:
        shp_base = temp_shp_dir / "cadastral_survey"
        
        # Create Polygon shapefile
        with shapefile.Writer(str(shp_base), shapeType=shapefile.POLYGON) as w:
            w.field("NAME", "C", size=50)
            w.field("ZONE", "C", size=20)
            w.field("TAX_LOT", "N", decimal=0)
            
            # Feature 1: Commercial Parcel (Clockwise for Shapefile standard)
            poly1 = [
                [-122.340, 47.604],
                [-122.336, 47.604],
                [-122.336, 47.600],
                [-122.340, 47.600],
                [-122.340, 47.604]
            ]
            w.poly([poly1])
            w.record("Commercial District Alpha", "Commercial-1", 101)
            
            # Feature 2: Residential Parcel (Clockwise for Shapefile standard)
            poly2 = [
                [-122.334, 47.603],
                [-122.331, 47.603],
                [-122.331, 47.601],
                [-122.334, 47.601],
                [-122.334, 47.603]
            ]
            w.poly([poly2])
            w.record("Greenwood Residential", "Residential-2", 102)
        
        # Write WKT for EPSG:4326 in .prj file
        prj_wkt = (
            'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
            'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
        )
        (temp_shp_dir / "cadastral_survey.prj").write_text(prj_wkt, encoding="utf-8")
        
        # Package into zip
        zip_path = output_dir / "sample_shapefile.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                f = temp_shp_dir / f"cadastral_survey{ext}"
                if f.exists():
                    zf.write(f, arcname=f"cadastral_survey{ext}")
                    
    finally:
        import shutil
        shutil.rmtree(temp_shp_dir, ignore_errors=True)

if __name__ == "__main__":
    generate_samples(Path(__file__).parent)
    print("Sample files generated successfully.")
