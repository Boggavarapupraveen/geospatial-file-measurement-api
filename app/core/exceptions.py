"""
Custom domain exceptions for Geospatial processing.
"""


class GeospatialAPIException(Exception):
    """Base exception for all domain-specific errors."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvalidFileFormatException(GeospatialAPIException):
    """Raised when an uploaded file is not an allowed format or is corrupted."""
    def __init__(self, message: str = "Invalid file format. Only .zip (Shapefile) and .kml are supported."):
        super().__init__(message, status_code=400)


class FileProcessingException(GeospatialAPIException):
    """Raised when processing a geospatial file fails."""
    def __init__(self, message: str = "Failed to process geospatial file."):
        super().__init__(message, status_code=422)


class FileNotFoundInStorageException(GeospatialAPIException):
    """Raised when the requested file ID is not found in the storage."""
    def __init__(self, file_id: str):
        super().__init__(f"Geospatial file with ID '{file_id}' not found.", status_code=404)


class UnsupportedGeometryException(GeospatialAPIException):
    """Raised when a geometry type cannot be measured."""
    def __init__(self, geom_type: str):
        super().__init__(f"Geometry type '{geom_type}' is not supported for measurement.", status_code=422)


class CRSTransformationException(GeospatialAPIException):
    """Raised when CRS detection or reprojection fails."""
    def __init__(self, message: str = "CRS transformation failed."):
        super().__init__(message, status_code=422)
