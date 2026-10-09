"""
Shapefile Parser Service.
Extracts and parses zipped ESRI Shapefiles (.shp, .shx, .dbf, .prj).
"""
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List, Tuple, Dict, Any

import shapefile
from shapely.geometry import shape, mapping

from app.core.logging import logger
from app.core.exceptions import InvalidFileFormatException, FileProcessingException
from app.models.file_models import RawFeature
from app.services.crs_service import crs_service


class ShapefileParser:
    """Extracts and parses ESRI Shapefiles from zip archives."""

    @staticmethod
    def _sanitize_record(record_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizes DBF attribute dictionary to JSON-serializable primitives."""
        sanitized = {}
        for k, v in record_dict.items():
            if isinstance(v, bytes):
                try:
                    sanitized[k] = v.decode("utf-8", errors="replace")
                except Exception:
                    sanitized[k] = str(v)
            elif hasattr(v, "isoformat"):  # date or datetime
                sanitized[k] = v.isoformat()
            else:
                sanitized[k] = v
        return sanitized

    def parse(self, zip_path: Path) -> Tuple[List[RawFeature], str]:
        """
        Unzips archive to a secure temporary directory, finds the .shp file,
        reads the .prj projection file, and extracts all geospatial features.
        
        Returns:
            Tuple[List[RawFeature], str]: Extracted features and the detected CRS.
        """
        temp_dir = tempfile.mkdtemp(prefix="shp_extract_")
        try:
            # 1. Safely extract zip archive
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for member in zf.infolist():
                        # Prevent directory traversal vulnerability (Zip Slip)
                        target_path = os.path.abspath(os.path.join(temp_dir, member.filename))
                        if not target_path.startswith(os.path.abspath(temp_dir)):
                            raise InvalidFileFormatException(f"Dangerous zip file entry detected: {member.filename}")
                    zf.extractall(temp_dir)
            except zipfile.BadZipFile as e:
                raise InvalidFileFormatException(f"Uploaded zip archive is invalid or corrupted: {e}")

            # 2. Locate .shp file
            shp_files = list(Path(temp_dir).rglob("*.shp"))
            if not shp_files:
                raise InvalidFileFormatException("Archive does not contain any .shp (Shapefile) file.")

            # Select primary shapefile (first found)
            shp_file = shp_files[0]
            base_stem = shp_file.stem
            parent_dir = shp_file.parent

            # 3. Read CRS from .prj file if available
            prj_file = parent_dir / f"{base_stem}.prj"
            detected_crs_str = "EPSG:4326"
            if prj_file.exists():
                try:
                    with open(prj_file, "r", encoding="utf-8", errors="ignore") as pf:
                        prj_wkt = pf.read().strip()
                        if prj_wkt:
                            _, detected_crs_str = crs_service.parse_crs(prj_wkt)
                            logger.info(f"Detected CRS from .prj: {detected_crs_str}")
                except Exception as e:
                    logger.warning(f"Error parsing .prj file: {e}. Defaulting to EPSG:4326")

            # 4. Read Shapefile records and geometries
            try:
                reader = shapefile.Reader(str(shp_file))
            except Exception as e:
                raise FileProcessingException(f"Failed to open Shapefile with PyShp: {str(e)}")

            raw_features: List[RawFeature] = []
            shape_records = reader.shapeRecords()
            logger.info(f"Shapefile '{shp_file.name}' opened successfully. Total records: {len(shape_records)}")

            for idx, sr in enumerate(shape_records):
                feat_id = str(idx)
                
                # Extract GeoJSON geometry via __geo_interface__
                geo_interface = sr.shape.__geo_interface__
                try:
                    geom = shape(geo_interface)
                    geom_type = geom.geom_type
                    geom_geojson = mapping(geom)
                except Exception as e:
                    logger.warning(f"Feature {idx} geometry could not be parsed: {e}")
                    geom_type = "Unknown"
                    geom_geojson = geo_interface

                # Extract attributes from DBF record
                record_dict = sr.record.as_dict()
                clean_properties = self._sanitize_record(record_dict)

                raw_features.append(
                    RawFeature(
                        feature_id=feat_id,
                        geometry_type=geom_type,
                        geometry=geom_geojson,
                        crs=detected_crs_str,
                        properties=clean_properties,
                    )
                )

            return raw_features, detected_crs_str

        finally:
            # Clean up temporary extracted directory
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir {temp_dir}: {e}")


shapefile_parser = ShapefileParser()
