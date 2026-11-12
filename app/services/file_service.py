from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from shapely.geometry import mapping

from app.config import UPLOAD_DIR
from app.models.schemas import (
    FeatureDetail,
    FileDetailResponse,
    FileInfo,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
)
from app.services.kml_parser import KMLParser
from app.services.measurement import MeasurementService
from app.services.shapefile_parser import ShapefileParser

logger = logging.getLogger(__name__)


class FileProcessingService:
    """
    Coordinates file storage, format detection, geospatial parsing,
    measurement calculations, and retrieval of processed file records.
    """

    # In-memory index of processed files (backed by disk metadata)
    _files_cache: Dict[str, FileDetailResponse] = {}

    @classmethod
    def initialize(cls):
        """Loads previously saved file records from UPLOAD_DIR on startup."""
        cls._files_cache.clear()
        if not UPLOAD_DIR.exists():
            return

        for meta_file in UPLOAD_DIR.glob("*/meta.json"):
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
                detail = FileDetailResponse(**data)
                cls._files_cache[detail.id] = detail
            except Exception as e:
                logger.warning("Could not load cached file metadata from %s: %s", meta_file, e)

    @classmethod
    def save_to_disk(cls, detail: FileDetailResponse):
        """Persists file detail to disk for resilience."""
        file_dir = UPLOAD_DIR / detail.id
        file_dir.mkdir(parents=True, exist_ok=True)
        meta_path = file_dir / "meta.json"
        meta_path.write_text(detail.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def process_uploaded_file(
        cls,
        filename: str,
        file_bytes: bytes,
    ) -> FileDetailResponse:
        """
        Processes an uploaded geospatial file (.zip Shapefile or .kml).
        """
        file_id = uuid.uuid4().hex[:8]
        now_iso = datetime.now(timezone.utc).isoformat()
        lower_name = filename.lower()

        # Determine file type
        if lower_name.endswith(".zip"):
            file_type = "SHAPEFILE_ZIP"
        elif lower_name.endswith(".kml"):
            file_type = "KML"
        else:
            raise ValueError(
                f"Unsupported file format '{filename}'. Please upload a .kml file or a .zip Shapefile archive."
            )

        file_dir = UPLOAD_DIR / file_id
        file_dir.mkdir(parents=True, exist_ok=True)
        saved_file_path = file_dir / filename
        saved_file_path.write_bytes(file_bytes)

        try:
            # Parse features and CRS
            if file_type == "SHAPEFILE_ZIP":
                raw_features, source_crs, crs_str = ShapefileParser.parse_zip(saved_file_path)
            else:
                raw_features, source_crs, crs_str = KMLParser.parse_file(saved_file_path)

            features: List[FeatureDetail] = []
            geometry_summary: Dict[str, int] = {}

            for idx, item in enumerate(raw_features):
                geom = item["geometry"]
                geom_type = item["geom_type"]
                props = item["properties"]
                feat_id = item.get("id", idx + 1)

                # Geometry summary count
                geometry_summary[geom_type] = geometry_summary.get(geom_type, 0) + 1

                # Calculate measurements using CRS reprojection strategy
                measurement = MeasurementService.calculate_measurement(geom, source_crs)

                # Convert Shapely geometry to standard GeoJSON dict
                geojson_geom = mapping(geom)

                features.append(
                    FeatureDetail(
                        id=feat_id,
                        geometry_type=geom_type,
                        crs=crs_str,
                        geometry=geojson_geom,
                        properties=props,
                        measurement=measurement,
                    )
                )

            detail = FileDetailResponse(
                id=file_id,
                filename=filename,
                file_type=file_type,
                feature_count=len(features),
                crs=crs_str,
                status="COMPLETED",
                geometry_summary=geometry_summary,
                created_at=now_iso,
                features=features,
            )

            cls._files_cache[file_id] = detail
            cls.save_to_disk(detail)
            return detail

        except Exception as e:
            logger.error("Processing failed for %s (id: %s): %s", filename, file_id, e, exc_info=True)
            failed_detail = FileDetailResponse(
                id=file_id,
                filename=filename,
                file_type=file_type,
                feature_count=0,
                crs="UNKNOWN",
                status="FAILED",
                geometry_summary={},
                created_at=now_iso,
                error_message=str(e),
                features=[],
            )
            cls._files_cache[file_id] = failed_detail
            cls.save_to_disk(failed_detail)
            return failed_detail

    @classmethod
    def get_file(cls, file_id: str) -> Optional[FileDetailResponse]:
        """Retrieves a processed file record by ID."""
        return cls._files_cache.get(file_id)

    @classmethod
    def list_files(cls) -> List[FileInfo]:
        """Lists metadata for all uploaded and processed files."""
        return [
            FileInfo(
                id=f.id,
                filename=f.filename,
                file_type=f.file_type,
                feature_count=f.feature_count,
                crs=f.crs,
                status=f.status,
                geometry_summary=f.geometry_summary,
                created_at=f.created_at,
                error_message=f.error_message,
            )
            for f in sorted(
                cls._files_cache.values(),
                key=lambda x: x.created_at,
                reverse=True,
            )
        ]

    @classmethod
    def get_geojson(cls, file_id: str) -> Optional[GeoJSONFeatureCollection]:
        """Constructs an RFC 7946 GeoJSON FeatureCollection for map rendering."""
        record = cls.get_file(file_id)
        if not record or record.status != "COMPLETED":
            return None

        geojson_features: List[GeoJSONFeature] = []
        for feat in record.features:
            props = dict(feat.properties)
            props["_id"] = feat.id
            props["_geom_type"] = feat.geometry_type
            props["_crs"] = feat.crs
            props["_measurement"] = feat.measurement.model_dump()

            geojson_features.append(
                GeoJSONFeature(
                    id=feat.id,
                    geometry=feat.geometry,
                    properties=props,
                )
            )

        return GeoJSONFeatureCollection(
            name=record.filename,
            features=geojson_features,
        )

    @classmethod
    def delete_file(cls, file_id: str) -> bool:
        """Deletes a file and its directory."""
        if file_id in cls._files_cache:
            del cls._files_cache[file_id]
        
        file_dir = UPLOAD_DIR / file_id
        if file_dir.exists():
            import shutil
            shutil.rmtree(file_dir, ignore_errors=True)
            return True
        return False

