"""
File Processor Service.
Orchestrates file upload validation, parsing, measurement calculation, and persistence.
"""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    InvalidFileFormatException,
    FileProcessingException,
    GeospatialAPIException,
)
from app.models.file_models import (
    FileInfoResponse,
    FileUploadResponse,
    FileProcessingStatus,
    GeospatialFileType,
    RawFeature,
)
from app.models.measurement_models import FileMeasurementsResponse
from app.services.shapefile_parser import shapefile_parser
from app.services.kml_parser import kml_parser
from app.services.measurement_service import measurement_service
from app.services.storage_service import storage_service


class FileProcessorService:
    """Coordinates parsing, projection, and measurement calculation for uploaded geospatial files."""

    @staticmethod
    def _detect_file_type(filename: str) -> GeospatialFileType:
        """Determines the geospatial file type from extension."""
        lower_name = filename.lower()
        if lower_name.endswith(".zip"):
            return GeospatialFileType.SHAPEFILE_ZIP
        elif lower_name.endswith(".kml"):
            return GeospatialFileType.KML
        return GeospatialFileType.UNKNOWN

    async def process_uploaded_file(self, file: UploadFile) -> FileUploadResponse:
        """
        Receives an uploaded file, validates format and size, extracts geospatial features,
        calculates measurements, and stores results.
        """
        filename = file.filename or "unknown_file"
        file_type = self._detect_file_type(filename)

        if file_type == GeospatialFileType.UNKNOWN:
            raise InvalidFileFormatException(
                f"Unsupported file format for '{filename}'. Allowed formats: .zip (Shapefile) or .kml"
            )

        file_id = str(uuid.uuid4())
        upload_time_iso = datetime.now(timezone.utc).isoformat()
        
        # Secure local destination
        dest_path = settings.UPLOAD_DIR / f"{file_id}_{filename}"
        
        # Read file contents and validate size
        try:
            content = await file.read()
            file_size = len(content)
            
            if file_size > settings.MAX_FILE_SIZE_BYTES:
                raise InvalidFileFormatException(
                    f"File size {file_size / (1024*1024):.1f}MB exceeds maximum limit of "
                    f"{settings.MAX_FILE_SIZE_BYTES / (1024*1024):.0f}MB."
                )

            with open(dest_path, "wb") as f:
                f.write(content)
                
            logger.info(f"Saved uploaded file '{filename}' ({file_size} bytes) to {dest_path}")
        except GeospatialAPIException:
            raise
        except Exception as e:
            logger.error(f"Failed to save upload '{filename}': {e}")
            raise FileProcessingException(f"Failed to save uploaded file: {str(e)}")

        # Initialize record with PENDING status
        initial_file_info = FileInfoResponse(
            id=file_id,
            filename=filename,
            file_type=file_type.value,
            feature_count=0,
            crs="UNKNOWN",
            status=FileProcessingStatus.PROCESSING.value,
            uploaded_at=upload_time_iso,
            processed_at=None,
            file_size_bytes=file_size,
            error=None,
        )
        storage_service.save_file_record(initial_file_info)

        # Process features and calculate measurements
        try:
            if file_type == GeospatialFileType.SHAPEFILE_ZIP:
                features, crs_str = shapefile_parser.parse(dest_path)
            elif file_type == GeospatialFileType.KML:
                features, crs_str = kml_parser.parse(dest_path)
            else:
                raise InvalidFileFormatException(f"Unhandled file type {file_type}")

            processed_time_iso = datetime.now(timezone.utc).isoformat()

            # Calculate measurements
            measurements: FileMeasurementsResponse = measurement_service.calculate_measurements(
                file_id=file_id,
                filename=filename,
                features=features,
                source_crs_str=crs_str,
            )

            # Update file info to COMPLETED
            completed_file_info = FileInfoResponse(
                id=file_id,
                filename=filename,
                file_type=file_type.value,
                feature_count=len(features),
                crs=crs_str,
                status=FileProcessingStatus.COMPLETED.value,
                uploaded_at=upload_time_iso,
                processed_at=processed_time_iso,
                file_size_bytes=file_size,
                error=None,
            )
            storage_service.save_file_record(
                file_info=completed_file_info,
                raw_features=features,
                measurements=measurements,
            )

            logger.info(
                f"Successfully processed file '{filename}' (ID: {file_id}). "
                f"Features: {len(features)}, CRS: {crs_str}"
            )

            return FileUploadResponse(
                id=file_id,
                filename=filename,
                file_type=file_type.value,
                feature_count=len(features),
                crs=crs_str,
                status=FileProcessingStatus.COMPLETED,
                uploaded_at=upload_time_iso,
                message=f"File '{filename}' processed successfully with {len(features)} features.",
            )

        except GeospatialAPIException as g_err:
            failed_info = FileInfoResponse(
                id=file_id,
                filename=filename,
                file_type=file_type.value,
                feature_count=0,
                crs="UNKNOWN",
                status=FileProcessingStatus.FAILED.value,
                uploaded_at=upload_time_iso,
                processed_at=datetime.now(timezone.utc).isoformat(),
                file_size_bytes=file_size,
                error=g_err.message,
            )
            storage_service.save_file_record(failed_info)
            raise

        except Exception as err:
            logger.exception(f"Unexpected error processing {filename}: {err}")
            failed_info = FileInfoResponse(
                id=file_id,
                filename=filename,
                file_type=file_type.value,
                feature_count=0,
                crs="UNKNOWN",
                status=FileProcessingStatus.FAILED.value,
                uploaded_at=upload_time_iso,
                processed_at=datetime.now(timezone.utc).isoformat(),
                file_size_bytes=file_size,
                error=str(err),
            )
            storage_service.save_file_record(failed_info)
            raise FileProcessingException(f"Processing error: {str(err)}")


file_processor = FileProcessorService()
