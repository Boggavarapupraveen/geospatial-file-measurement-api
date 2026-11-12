import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pyproj
import shapefile
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from app.services.crs_manager import CRSManager

logger = logging.getLogger(__name__)


class ShapefileParser:
    """
    Safely extracts and parses Shapefiles from a zipped archive (.zip).
    Extracts features, coordinates, attributes, and CRS definitions (.prj).
    """

    @classmethod
    def parse_zip(
        cls, zip_path: Path
    ) -> Tuple[List[Dict[str, Any]], pyproj.CRS, str]:
        """
        Parses a .zip file containing a Shapefile.
        Returns:
            (features_data, source_crs, crs_name)
        where each item in features_data contains:
            {'id': idx, 'geometry': shapely_geom, 'properties': dict, 'geom_type': str}
        """
        extract_dir = Path(tempfile.mkdtemp(prefix="shp_extract_"))
        try:
            # 1. Safely extract zip (prevent Zip Slip vulnerabilities)
            with zipfile.ZipFile(zip_path, "r") as zf:
                for member in zf.infolist():
                    target_path = extract_dir / member.filename
                    # Ensure extracted file stays within target directory
                    if not target_path.resolve().is_relative_to(extract_dir.resolve()):
                        raise ValueError(f"Malicious archive entry detected: {member.filename}")
                zf.extractall(extract_dir)

            # 2. Locate .shp file (could be in root or a subfolder inside the zip)
            shp_files = list(extract_dir.rglob("*.shp"))
            if not shp_files:
                raise ValueError("Invalid Shapefile archive: No .shp file found inside the zip.")

            shp_file = shp_files[0]
            base_stem = shp_file.stem
            parent_dir = shp_file.parent

            # 3. Read CRS from .prj file if present
            prj_file = parent_dir / f"{base_stem}.prj"
            source_crs = pyproj.CRS.from_epsg(4326)
            crs_name = "EPSG:4326 (Default)"

            if prj_file.exists():
                try:
                    wkt = prj_file.read_text(encoding="utf-8", errors="ignore").strip()
                    if wkt:
                        source_crs, crs_name = CRSManager.parse_crs(wkt)
                except Exception as pe:
                    logger.warning("Could not parse .prj file %s: %s", prj_file, pe)

            # 4. Read Shapefile records
            features: List[Dict[str, Any]] = []
            with shapefile.Reader(str(shp_file)) as reader:
                field_names = [field[0] for field in reader.fields[1:]]  # exclude deletion flag

                for idx, shape_rec in enumerate(reader.shapeRecords()):
                    try:
                        raw_geom = shape_rec.shape.__geo_interface__
                        geom_obj: BaseGeometry = shape(raw_geom)
                        
                        # Extract record attributes
                        record_dict = {}
                        for f_name, f_val in zip(field_names, shape_rec.record):
                            # Convert non-serializable objects (like dates/bytes) to strings
                            if isinstance(f_val, bytes):
                                try:
                                    f_val = f_val.decode("utf-8", errors="replace").strip()
                                except Exception:
                                    f_val = str(f_val)
                            elif hasattr(f_val, "isoformat"):
                                f_val = f_val.isoformat()
                            record_dict[f_name] = f_val

                        feature_id = shape_rec.record[0] if shape_rec.record else idx
                        features.append({
                            "id": str(feature_id) if feature_id is not None else str(idx),
                            "geometry": geom_obj,
                            "geom_type": geom_obj.geom_type,
                            "properties": record_dict,
                        })
                    except Exception as fe:
                        logger.warning("Error parsing shapefile record %d: %s", idx, fe)
                        continue

            return features, source_crs, crs_name

        finally:
            # Clean up extracted temp directory
            shutil.rmtree(extract_dir, ignore_errors=True)

