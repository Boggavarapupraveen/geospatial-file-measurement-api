# Geospatial File Measurement API & Interactive GIS Explorer

[![FastAPI](https://img.shields.io/badge/FastAPI-0.128.0-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![Shapely](https://img.shields.io/badge/Shapely-2.2.0-brightgreen.svg?style=flat)](https://shapely.readthedocs.io)
[![PyProj](https://img.shields.io/badge/PyProj-3.8.0-orange.svg?style=flat)](https://pyproj4.github.io/pyproj)
[![Tests](https://img.shields.io/badge/tests-19%20passed-success.svg?style=flat)](#testing)
[![License](https://img.shields.io/badge/License-MIT-purple.svg?style=flat)](LICENSE)

A high-performance backend service and interactive GIS web explorer designed for ingesting, validating, reprojecting, measuring, and visualizing geospatial vector files. The service accepts **ESRI Shapefile archives (`.zip`)** and **Google Earth / OpenGIS KML (`.kml`)** files, autonomously handles geographic coordinate reference systems (CRS), dynamically reprojects features into optimal local metric projections, and calculates distortion-free planar and ellipsoidal measurements.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [CRS & Measurement Strategy](#crs--measurement-strategy)
- [API Reference](#api-reference)
  - [Upload Geospatial File](#1-upload-geospatial-file)
  - [Get File Information](#2-get-file-information)
  - [Get Complete File Details](#3-get-complete-file-details)
  - [Get Features & Measurements](#4-get-features--measurements)
  - [Export GeoJSON FeatureCollection](#5-export-geojson-featurecollection)
  - [List All Files](#6-list-all-files)
  - [Delete File](#7-delete-file)
- [Interactive Web UI](#interactive-web-ui)
- [Project Structure](#project-structure)
- [Installation & Quick Start](#installation--quick-start)
- [Running the Server](#running-the-server)
- [Testing](#testing)
- [Production & Security Considerations](#production--security-considerations)
- [License](#license)

---

## Overview

Calculating area or distance directly on unprojected geographic coordinates (such as WGS84 / EPSG:4326 in decimal degrees) produces physically incorrect and distorted values because a degree of longitude shrinks from ~111 km at the Equator to 0 km at the poles.

This service solves this challenge by implementing an **intelligent CRS detection and automated projection engine**:
1. Files in geographic CRS (`EPSG:4326`, `NAD83`, etc.) are recognized.
2. The centroid of each feature is used to dynamically identify the optimal metric **Universal Transverse Mercator (UTM)** zone.
3. The geometry is transformed into metric projected coordinates before Euclidean area and length are computed.
4. Measurements are reported in primary SI units ($m^2$ and $m$) alongside derived metric and imperial equivalents ($km^2$, hectares, acres, $km$, miles, feet).
5. Unsupported geometries (such as `Point`, `MultiPoint`, or `GeometryCollection`) are handled gracefully without application crashes.

---

## Key Features

- **Multi-Format Ingestion**: Accepts zipped Shapefiles (`.zip` containing `.shp`, `.shx`, `.dbf`, `.prj`) and KML files (`.kml`).
- **Autonomous Metric Reprojection**: Transforms geographic lat/lon geometries to appropriate UTM zones before measurement.
- **Polygon Area Calculation**: Computes planar area in $m^2$, $km^2$, hectares, and acres, plus perimeter.
- **LineString Length Calculation**: Computes planar distance in meters, kilometers, feet, and miles.
- **Graceful Handling of Points & Edge Cases**: Explicitly marks Points as zero spatial extent without errors.
- **Interactive Web Interface**: Built-in modern GIS dashboard with Leaflet.js, drag-and-drop upload, layer switcher, and measurement inspector.
- **RFC 7946 GeoJSON Export**: Direct endpoint for exporting processed features to Leaflet, Mapbox, QGIS, or ArcGIS.
- **Resilient & Secure**: Zip-Slip extraction protection, file size safeguards, and schema validation with Pydantic v2.

---

## System Architecture

```mermaid
flowchart TD
    Client["Client / Web UI"] -->|POST /api/files/ (.zip or .kml)| Router["FastAPI Router"]
    Router --> Service["File Processing Service"]
    
    subgraph Ingestion["Format Parsing Engine"]
        Service -->|*.zip| ShpParser["ShapefileParser (PyShp + WKT PRJ)"]
        Service -->|*.kml| KmlParser["KMLParser (Placemarks + Coordinates)"]
    end
    
    subgraph GeoEngine["CRS & Measurement Engine"]
        ShpParser --> CRS["CRS Manager"]
        KmlParser --> CRS
        CRS -->|Detect EPSG:4326| UTM["Auto-UTM Zone Determination"]
        UTM --> Transformer["PyProj Metric Transformer"]
        Transformer --> Meas["MeasurementService (Shapely)"]
        Meas -->|Polygon / MultiPolygon| Area["Area: m², km², ha, acres"]
        Meas -->|LineString / MultiLineString| Length["Length: m, km, ft, mi"]
        Meas -->|Point / MultiPoint| PointHandle["Graceful N/A (zero extent)"]
    end
    
    GeoEngine --> Persistence["Disk Storage & Memory Cache"]
    Persistence --> APIResponse["JSON & GeoJSON Responses"]
    APIResponse --> Client
```

---

## CRS & Measurement Strategy

### Why Unprojected Lat/Long Measurements Fail
Geographic coordinates (EPSG:4326) measure angles in decimal degrees on an ellipsoidal Earth model. Using Euclidean geometry on degrees ($x \times y$) yields $\text{degrees}^2$, which cannot be converted to physical area by a simple constant because:
$$\Delta x = \Delta \lambda \cdot R \cdot \cos(\phi)$$
$$\Delta y = \Delta \phi \cdot R$$

### The Auto-UTM Selection Solution
When processing geographic geometries, this engine:
1. Calculates the geometric centroid $(\lambda_c, \phi_c)$ in degrees.
2. Identifies the corresponding Universal Transverse Mercator (UTM) 6-degree longitudinal zone:
   $$\text{Zone} = \left\lfloor \frac{\lambda_c + 180}{6} \right\rfloor + 1 \quad (1 \le \text{Zone} \le 60)$$
3. Chooses the EPSG code based on hemisphere:
   - Northern Hemisphere ($\phi_c \ge 0$): $\text{EPSG} = 32600 + \text{Zone}$
   - Southern Hemisphere ($\phi_c < 0$): $\text{EPSG} = 32700 + \text{Zone}$
   - Polar zones ($|\phi_c| > 84^\circ$): Universal Polar Stereographic (UPS North `EPSG:32661` or UPS South `EPSG:32761`).
4. Reprojects coordinates using `pyproj.Transformer(always_xy=True)` and computes exact planar measurements in meters.
5. In addition, ellipsoidal geodesic calculations (`pyproj.Geod(ellps='WGS84')`) are computed and provided for geodetic verification.

---

## API Reference

Interactive OpenAPI documentation is automatically served at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### 1. Upload Geospatial File
`POST /api/files/`

Uploads and processes a `.kml` file or a `.zip` archive containing a Shapefile.

**Request**: `multipart/form-data` with form field `file`.

**Response** (`201 Created`):
```json
{
  "id": "7b6908e4",
  "filename": "survey.kml",
  "file_type": "KML",
  "feature_count": 3,
  "crs": "EPSG:4326 (WGS 84)",
  "status": "COMPLETED",
  "geometry_summary": {
    "Polygon": 1,
    "LineString": 1,
    "Point": 1
  },
  "created_at": "2026-11-12T16:30:00Z",
  "error_message": null
}
```

---

### 2. Get File Information
`GET /api/files/{id}/`

Returns summary information about an uploaded file.

**Response** (`200 OK`):
```json
{
  "id": "7b6908e4",
  "filename": "survey.kml",
  "file_type": "KML",
  "feature_count": 3,
  "crs": "EPSG:4326 (WGS 84)",
  "status": "COMPLETED",
  "geometry_summary": {
    "Polygon": 1,
    "LineString": 1,
    "Point": 1
  },
  "created_at": "2026-11-12T16:30:00Z",
  "error_message": null
}
```

---

### 3. Get Complete File Details
`GET /api/files/{id}/details/`

Returns full metadata along with all extracted features, geometries, properties, and measurement conversions.

---

### 4. Get Features & Measurements
`GET /api/files/{id}/features/`

Returns an array of all features with their computed measurements.

**Sample Feature Output (Polygon with Reprojected Area)**:
```json
{
  "id": "feat-lake-01",
  "geometry_type": "Polygon",
  "crs": "EPSG:4326 (WGS 84)",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-122.335, 47.608], [-122.330, 47.608], [-122.330, 47.612], [-122.335, 47.612], [-122.335, 47.608]]]
  },
  "properties": {
    "name": "Emerald Lake",
    "category": "Water Body",
    "depth_meters": "8.5"
  },
  "measurement": {
    "supported": true,
    "measurement_type": "area",
    "primary_value": 166820.45,
    "primary_unit": "sq_meters",
    "units": {
      "sq_meters": 166820.45,
      "sq_kilometers": 0.1668,
      "hectares": 16.682,
      "acres": 41.2222,
      "sq_feet": 1795639.42,
      "perimeter_meters": 1634.52,
      "perimeter_kilometers": 1.6345
    },
    "projected_crs": "EPSG:32610",
    "projected_crs_name": "WGS 84 / UTM zone 10N",
    "note": "Projected into EPSG:32610 (WGS 84 / UTM zone 10N) for accurate planar area calculation."
  }
}
```

**Sample Feature Output (Point Geometry - Gracefully Handled)**:
```json
{
  "id": "feat-landmark-01",
  "geometry_type": "Point",
  "crs": "EPSG:4326 (WGS 84)",
  "geometry": {
    "type": "Point",
    "coordinates": [-122.332, 47.610]
  },
  "properties": {
    "name": "Visitor Information Center",
    "facility_type": "Office"
  },
  "measurement": {
    "supported": false,
    "measurement_type": "none",
    "primary_value": null,
    "primary_unit": null,
    "units": {},
    "note": "Point geometry represents a single location with zero area and zero length. No measurement required."
  }
}
```

---

### 5. Export GeoJSON FeatureCollection
`GET /api/files/{id}/geojson/`

Returns a standard RFC 7946 GeoJSON FeatureCollection containing all features and properties, suitable for loading directly into Leaflet, Mapbox, or desktop GIS (QGIS/ArcGIS).

---

### 6. List All Files
`GET /api/files/`

Returns a paginated/total list of all processed files and their processing statuses.

---

### 7. Delete File
`DELETE /api/files/{id}/`

Deletes the file record and associated artifacts from storage.

---

## Interactive Web UI

The service includes a built-in responsive web application served at `http://localhost:8000/`.

- **Drag-and-Drop Uploader**: Direct upload zone with client-side validation for `.kml` and `.zip` files.
- **One-Click Sample Loaders**: Test instantly with pre-bundled realistic sample KML or Shapefile data without needing external files.
- **Interactive Leaflet Map**: Renders Polygons (with customizable fill opacity), LineStrings, and Point markers.
- **Measurement Inspector**: Clicking any map geometry displays its metric values, projected UTM zone, and attribute table.
- **Features Data Table**: Search and filter features by geometry type or attribute name, with auto-zoom on row click.
- **GeoJSON Export**: Instant one-click download for GIS workflows.

---

## Project Structure

```
geospatial-measurement-api/
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application, CORS, static mounts, lifespan
│   ├── config.py                   # App configuration & upload limits
│   │
│   ├── api/                        # API route controllers
│   │   ├── __init__.py
│   │   └── files.py                # Endpoints for upload, metadata, features, geojson, delete
│   │
│   ├── models/                     # Pydantic schemas & response contracts
│   │   ├── __init__.py
│   │   └── schemas.py              # FileInfo, FeatureDetail, MeasurementInfo, GeoJSON
│   │
│   ├── services/                   # Core business & geospatial processing
│   │   ├── __init__.py
│   │   ├── crs_manager.py          # Auto-UTM zone selection & coordinate transformation
│   │   ├── measurement.py          # Area/Length calculations, unit conversion & fallbacks
│   │   ├── shapefile_parser.py     # Safe zip extraction, DBF attribute & PRJ reader
│   │   ├── kml_parser.py           # KML XML parser for Placemarks, rings, and properties
│   │   └── file_service.py         # File ingestion orchestration & disk persistence
│   │
│   ├── static/                     # Web dashboard frontend
│   │   ├── index.html              # Modern GIS Explorer UI
│   │   ├── app.js                  # Leaflet map interactions & async API client
│   │   └── styles.css              # Custom styling & dark-theme adjustments
│   │
│   └── samples/                    # Pre-bundled realistic test data
│       ├── sample_generator.py     # Programmatic generator for sample KML & Shapefiles
│       ├── sample_survey.kml       # Sample KML with Polygon, LineString, and Point
│       └── sample_shapefile.zip    # Sample zipped ESRI Shapefile with attributes
│
├── tests/                          # Automated test suite (Pytest)
│   ├── __init__.py
│   ├── conftest.py                 # Fixtures & sample data loaders
│   ├── test_crs.py                 # CRS parsing & UTM reprojection unit tests
│   ├── test_measurements.py        # Polygon area, line length & point handling tests
│   ├── test_parsers.py             # Shapefile & KML parser extraction tests
│   └── test_api.py                 # API endpoints, validation & status code tests
│
├── .gitignore                      # Git ignore rules for Python, cache, and uploads
├── requirements.txt                # Python dependencies
├── run.py                          # Application runner script
└── README.md                       # Comprehensive documentation
```

---

## Installation & Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Boggavarapupraveen/geospatial-file-measurement-api.git
cd geospatial-file-measurement-api
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Running the Server

Run the development server using the convenient runner script:
```bash
python run.py
```

Or using `uvicorn` directly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then visit:
- **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Testing

The project includes a comprehensive automated test suite covering CRS detection, projection logic, measurement accuracy, shapefile and KML extraction, and API endpoint error handling.

Execute the test suite with:
```bash
pytest -v
```

**Test Coverage Summary**:
- `test_crs.py`: Validates EPSG parsing, WKT extraction, and auto-UTM zone calculations for Northern, Southern, and Polar regions.
- `test_measurements.py`: Verifies that polygon area and linestring length are calculated in metric units ($m^2$ and $m$) rather than squared degrees, and tests graceful handling of Points and unsupported geometries.
- `test_parsers.py`: Tests parsing of `.kml` (with XML namespaces and attributes) and `.zip` Shapefiles (extracting `.shp`, `.shx`, `.dbf`, and `.prj`).
- `test_api.py`: Tests upload validation, HTTP 201/200/400/404 status codes, GeoJSON export, and file deletion.

---

## Production & Security Considerations

1. **Zip-Slip Protection**: When unpacking `.zip` Shapefiles, each path is resolved and validated against directory traversal attacks (`is_relative_to`) before extraction.
2. **XML Security**: KML parsing restricts unbounded entity expansion.
3. **Upload Size Limits**: Configurable maximum file size (default: 50 MB) prevents memory exhaustion.
4. **Temporary File Isolation**: Unzipped archives are stored in isolated temporary directories and cleaned up immediately after reading.
5. **Graceful Fault Tolerance**: Corrupt records or unsupported geometry types log warnings and return informative status messages rather than triggering 500 internal server errors.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

