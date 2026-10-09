"""
KML (Keyhole Markup Language) Parser Service.
Parses OGC KML 2.2 files safely, extracting Placemarks, Geometries, and ExtendedData.
"""
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import xml.etree.ElementTree as ET

import defusedxml.ElementTree as DefusedET
from shapely.geometry import (
    Point,
    LineString,
    Polygon,
    MultiPoint,
    MultiLineString,
    MultiPolygon,
    GeometryCollection,
    mapping,
)
from shapely.geometry.base import BaseGeometry

from app.core.logging import logger
from app.core.exceptions import InvalidFileFormatException, FileProcessingException
from app.models.file_models import RawFeature


class KMLParser:
    """Parses KML 2.2 XML files into structured geospatial features."""

    @staticmethod
    def _parse_coord_string(coord_str: str) -> List[Tuple[float, float]]:
        """
        Parses a KML coordinates whitespace/newline-separated string.
        Each coordinate is 'lon,lat' or 'lon,lat,alt'.
        Returns list of (lon, lat) tuples.
        """
        coords: List[Tuple[float, float]] = []
        if not coord_str:
            return coords

        tokens = coord_str.strip().split()
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            parts = token.split(",")
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    coords.append((lon, lat))
                except ValueError:
                    continue
        return coords

    def _parse_polygon_elem(self, poly_elem: ET.Element) -> Optional[Polygon]:
        """Parses a <Polygon> element with outer and inner boundary rings."""
        outer_elem = poly_elem.find(".//outerBoundaryIs//coordinates")
        if outer_elem is None or not outer_elem.text:
            return None

        outer_coords = self._parse_coord_string(outer_elem.text)
        if len(outer_coords) < 3:
            return None

        inner_rings: List[List[Tuple[float, float]]] = []
        for inner_elem in poly_elem.findall(".//innerBoundaryIs//coordinates"):
            if inner_elem.text:
                inner_coords = self._parse_coord_string(inner_elem.text)
                if len(inner_coords) >= 3:
                    inner_rings.append(inner_coords)

        try:
            return Polygon(outer_coords, inner_rings)
        except Exception as e:
            logger.warning(f"Error constructing Polygon: {e}")
            return None

    def _parse_linestring_elem(self, line_elem: ET.Element) -> Optional[LineString]:
        """Parses a <LineString> element."""
        coord_elem = line_elem.find(".//coordinates")
        if coord_elem is None or not coord_elem.text:
            return None

        coords = self._parse_coord_string(coord_elem.text)
        if len(coords) < 2:
            return None

        try:
            return LineString(coords)
        except Exception as e:
            logger.warning(f"Error constructing LineString: {e}")
            return None

    def _parse_point_elem(self, pt_elem: ET.Element) -> Optional[Point]:
        """Parses a <Point> element."""
        coord_elem = pt_elem.find(".//coordinates")
        if coord_elem is None or not coord_elem.text:
            return None

        coords = self._parse_coord_string(coord_elem.text)
        if not coords:
            return None

        try:
            return Point(coords[0])
        except Exception as e:
            logger.warning(f"Error constructing Point: {e}")
            return None

    def _parse_geometry(self, placemark_elem: ET.Element) -> Optional[BaseGeometry]:
        """Extracts and parses geometry elements from a Placemark."""
        # 1. Direct Polygon
        poly_elem = placemark_elem.find(".//Polygon")
        if poly_elem is not None:
            return self._parse_polygon_elem(poly_elem)

        # 2. Direct LineString
        line_elem = placemark_elem.find(".//LineString")
        if line_elem is not None:
            return self._parse_linestring_elem(line_elem)

        # 3. Direct Point
        point_elem = placemark_elem.find(".//Point")
        if point_elem is not None:
            return self._parse_point_elem(point_elem)

        # 4. MultiGeometry container
        mg_elem = placemark_elem.find(".//MultiGeometry")
        if mg_elem is not None:
            sub_geoms: List[BaseGeometry] = []
            for child in mg_elem:
                tag = child.tag
                if tag == "Polygon":
                    g = self._parse_polygon_elem(child)
                    if g:
                        sub_geoms.append(g)
                elif tag == "LineString":
                    g = self._parse_linestring_elem(child)
                    if g:
                        sub_geoms.append(g)
                elif tag == "Point":
                    g = self._parse_point_elem(child)
                    if g:
                        sub_geoms.append(g)

            if not sub_geoms:
                return None

            # Check if all sub-geometries are of the same type
            if all(isinstance(g, Polygon) for g in sub_geoms):
                return MultiPolygon(sub_geoms)
            elif all(isinstance(g, LineString) for g in sub_geoms):
                return MultiLineString(sub_geoms)
            elif all(isinstance(g, Point) for g in sub_geoms):
                return MultiPoint(sub_geoms)
            else:
                return GeometryCollection(sub_geoms)

        return None

    def parse(self, kml_path: Path) -> Tuple[List[RawFeature], str]:
        """
        Parses a .kml file, extracting all Placemarks with their geometries and metadata.
        
        Returns:
            Tuple[List[RawFeature], str]: Extracted features and 'EPSG:4326'.
        """
        try:
            with open(kml_path, "rb") as f:
                tree = DefusedET.parse(f)
            root = tree.getroot()
        except Exception as e:
            logger.error(f"Failed to parse XML in KML file {kml_path.name}: {e}")
            raise InvalidFileFormatException(f"Invalid or corrupted KML XML file: {str(e)}")

        # Strip XML namespaces for uniform querying
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        placemarks = root.findall(".//Placemark")
        logger.info(f"KML '{kml_path.name}' parsed. Found {len(placemarks)} Placemarks.")

        features: List[RawFeature] = []
        crs_str = "EPSG:4326"  # KML standard specification is WGS 84 (EPSG:4326)

        for idx, pm in enumerate(placemarks):
            feat_id = pm.attrib.get("id", str(idx))
            name = pm.findtext("name")
            desc = pm.findtext("description")

            properties: Dict[str, Any] = {}
            if name:
                properties["name"] = name.strip()
            if desc:
                properties["description"] = desc.strip()

            # Parse ExtendedData
            ext_data = pm.find("ExtendedData")
            if ext_data is not None:
                for data_tag in ext_data.findall(".//Data"):
                    d_name = data_tag.attrib.get("name")
                    d_val = data_tag.findtext("value")
                    if d_name and d_val is not None:
                        properties[d_name] = d_val.strip()

                for sdata in ext_data.findall(".//SchemaData/SimpleData"):
                    s_name = sdata.attrib.get("name")
                    s_val = sdata.text
                    if s_name and s_val is not None:
                        properties[s_name] = s_val.strip()

            # Parse Geometry
            geom = self._parse_geometry(pm)
            if geom is not None and not geom.is_empty:
                geom_type = geom.geom_type
                geom_dict = mapping(geom)
            else:
                geom_type = "None"
                geom_dict = {"type": "None", "coordinates": []}

            features.append(
                RawFeature(
                    feature_id=feat_id,
                    geometry_type=geom_type,
                    geometry=geom_dict,
                    crs=crs_str,
                    properties=properties,
                )
            )

        return features, crs_str


kml_parser = KMLParser()
