"""
Storage Service.
Manages metadata, raw features, and calculated measurements in memory with persistence.
"""
from threading import Lock
from typing import Dict, List, Optional, Any

from app.models.file_models import FileInfoResponse, RawFeature
from app.models.measurement_models import FileMeasurementsResponse


class StorageService:
    """Thread-safe storage service for uploaded geospatial files and measurements."""

    def __init__(self):
        self._lock = Lock()
        self._file_metadata: Dict[str, FileInfoResponse] = {}
        self._raw_features: Dict[str, List[RawFeature]] = {}
        self._measurements: Dict[str, FileMeasurementsResponse] = {}

    def save_file_record(
        self,
        file_info: FileInfoResponse,
        raw_features: Optional[List[RawFeature]] = None,
        measurements: Optional[FileMeasurementsResponse] = None,
    ) -> None:
        """Saves or updates file metadata, features, and measurements."""
        with self._lock:
            self._file_metadata[file_info.id] = file_info
            if raw_features is not None:
                self._raw_features[file_info.id] = raw_features
            if measurements is not None:
                self._measurements[file_info.id] = measurements

    def get_file_info(self, file_id: str) -> Optional[FileInfoResponse]:
        """Retrieves file metadata by ID."""
        with self._lock:
            return self._file_metadata.get(file_id)

    def get_measurements(self, file_id: str) -> Optional[FileMeasurementsResponse]:
        """Retrieves calculated measurements by file ID."""
        with self._lock:
            return self._measurements.get(file_id)

    def get_raw_features(self, file_id: str) -> Optional[List[RawFeature]]:
        """Retrieves raw extracted features by file ID."""
        with self._lock:
            return self._raw_features.get(file_id)

    def list_files(self) -> List[FileInfoResponse]:
        """Lists all uploaded files sorted by upload time (descending)."""
        with self._lock:
            return list(self._file_metadata.values())

    def delete_file(self, file_id: str) -> bool:
        """Deletes file records from storage."""
        with self._lock:
            if file_id in self._file_metadata:
                del self._file_metadata[file_id]
                self._raw_features.pop(file_id, None)
                self._measurements.pop(file_id, None)
                return True
            return False

    def get_geojson_feature_collection(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Constructs a GeoJSON FeatureCollection from stored features."""
        with self._lock:
            features = self._raw_features.get(file_id)
            if features is None:
                return None

            geojson_features = []
            for feat in features:
                geojson_features.append({
                    "type": "Feature",
                    "id": feat.feature_id,
                    "geometry": feat.geometry,
                    "properties": {
                        **feat.properties,
                        "_feature_id": feat.feature_id,
                        "_geometry_type": feat.geometry_type,
                        "_crs": feat.crs,
                    },
                })

            return {
                "type": "FeatureCollection",
                "features": geojson_features,
            }


storage_service = StorageService()
