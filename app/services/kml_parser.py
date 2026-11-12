import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pyproj
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, MultiLineString, GeometryCollection
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)


def _strip_ns(tag: str) -> str:
    """Removes XML namespace prefix if present."""
    return tag.split("}")[-1] if "}" in tag else tag


def _parse_coord_string(text: str) -> List[Tuple[float, ...]]:
    """
    Parses KML coordinate tuples: 'lon,lat[,alt]' separated by whitespace or newlines.
    """
    coords = []
    tokens = re.split(r"\s+", text.strip())
    for token in tokens:
        if not token:
            continue
        parts = token.split(",")
        if len(parts) >= 2:
            try:
                lon = float(parts[0])
                lat = float(parts[1])
                if len(parts) >= 3:
                    alt = float(parts[2])
                    coords.append((lon, lat, alt))
                else:
                    coords.append((lon, lat))
            except ValueError:
                continue
    return coords


class KMLParser:
    """
    Parses standard OpenGIS KML 2.2 / Google Earth KML files into Shapely geometries
    and associated attribute properties.
    """

    @classmethod
    def parse_geometry_element(cls, elem: ET.Element) -> Optional[BaseGeometry]:
        """
        Parses a KML geometry XML element into a corresponding Shapely geometry.
        """
        tag = _strip_ns(elem.tag)

        if tag == "Point":
            coords_elem = elem.find("{*}coordinates")
            if coords_elem is not None and coords_elem.text:
                coords = _parse_coord_string(coords_elem.text)
                if coords:
                    return Point(coords[0])

        elif tag == "LineString":
            coords_elem = elem.find("{*}coordinates")
            if coords_elem is not None and coords_elem.text:
                coords = _parse_coord_string(coords_elem.text)
                if len(coords) >= 2:
                    return LineString(coords)

        elif tag == "Polygon":
            outer_elem = elem.find(".//{*}outerBoundaryIs//{*}coordinates")
            if outer_elem is not None and outer_elem.text:
                outer_coords = _parse_coord_string(outer_elem.text)
                if len(outer_coords) >= 3:
                    # Check for interior rings / holes
                    inner_rings = []
                    for inner_elem in elem.findall(".//{*}innerBoundaryIs//{*}coordinates"):
                        if inner_elem.text:
                            inner_coords = _parse_coord_string(inner_elem.text)
                            if len(inner_coords) >= 3:
                                inner_rings.append(inner_coords)
                    return Polygon(outer_coords, inner_rings)

        elif tag == "MultiGeometry":
            sub_geoms = []
            for child in elem:
                sub_g = cls.parse_geometry_element(child)
                if sub_g:
                    sub_geoms.append(sub_g)
            if not sub_geoms:
                return None
            
            # Check if all sub-geometries are Polygons
            if all(isinstance(g, Polygon) for g in sub_geoms):
                return MultiPolygon(sub_geoms)
            # Check if all sub-geometries are LineStrings
            if all(isinstance(g, LineString) for g in sub_geoms):
                return MultiLineString(sub_geoms)
            # Mixed geometries
            return GeometryCollection(sub_geoms)

        return None

    @classmethod
    def parse_file(
        cls, kml_path: Path
    ) -> Tuple[List[Dict[str, Any]], pyproj.CRS, str]:
        """
        Parses a KML file.
        Returns:
            (features_data, source_crs, crs_name)
        """
        try:
            tree = ET.parse(str(kml_path))
            root = tree.getroot()
        except Exception as e:
            raise ValueError(f"Failed to parse XML in KML file: {str(e)}")

        # KML by OpenGIS specification is always WGS 84 (EPSG:4326)
        source_crs = pyproj.CRS.from_epsg(4326)
        crs_name = "EPSG:4326 (WGS 84)"

        features: List[Dict[str, Any]] = []
        feature_index = 0

        # Find all Placemark elements regardless of nesting depth
        for placemark in root.iter():
            if _strip_ns(placemark.tag) != "Placemark":
                continue

            feature_index += 1
            pm_id = placemark.attrib.get("id", str(feature_index))

            name = ""
            description = ""
            properties: Dict[str, Any] = {}

            # Parse Placemark metadata
            for child in placemark:
                c_tag = _strip_ns(child.tag)
                if c_tag == "name":
                    name = (child.text or "").strip()
                elif c_tag == "description":
                    description = (child.text or "").strip()
                elif c_tag == "ExtendedData":
                    # Parse Data and SimpleData elements
                    for data_elem in child.iter():
                        d_tag = _strip_ns(data_elem.tag)
                        if d_tag in ("Data", "SimpleData"):
                            attr_name = data_elem.attrib.get("name")
                            val_elem = data_elem.find("{*}value")
                            attr_val = (
                                val_elem.text if val_elem is not None else data_elem.text
                            ) or ""
                            if attr_name:
                                properties[attr_name] = attr_val.strip()

            if name:
                properties["name"] = name
            if description:
                properties["description"] = description

            # Parse Geometry
            geom = None
            for child in placemark:
                geom = cls.parse_geometry_element(child)
                if geom is not None:
                    break

            if geom is not None:
                features.append({
                    "id": pm_id,
                    "geometry": geom,
                    "geom_type": geom.geom_type,
                    "properties": properties,
                })

        return features, source_crs, crs_name
