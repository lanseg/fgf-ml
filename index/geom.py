import math

import osmium
import pyproj
import shapely
from pyproj import Transformer
from shapely import strtree

DEFAULT_PROJ = "EPSG:4326"
DEFAULT_DATUM = "WGS84"

EARTH_RADIUS_KM = 6371.0
ZOOM_1KM = 14
WEB_MERCATOR_RADIUS = 6378137.0
WEB_MERCATOR_MAX = WEB_MERCATOR_RADIUS * math.pi  # ≈ 20037508.342789244
INITIAL_RESOLUTION = 2 * math.pi * WEB_MERCATOR_RADIUS / 256.0  # ≈ 156543 (metres/pixel at zoom 0)


def expand_bounding_box(lon1, lat1, lon2, lat2, add_m):
    """Expand using local UTM projection for best accuracy"""
    box = shapely.box(min(lon1, lon2), min(lat1, lat2), max(lon1, lon2), max(lat1, lat2))
    center = box.centroid
    local_crs = f"+proj=aeqd +lat_0={center.y} +lon_0={center.x} +datum={DEFAULT_DATUM} +units=m"

    to_metric = pyproj.Transformer.from_crs(DEFAULT_PROJ, local_crs, always_xy=True).transform

    to_wgs84 = pyproj.Transformer.from_crs(local_crs, DEFAULT_PROJ, always_xy=True).transform

    expanded = shapely.transform(box, to_metric, interleaved=False).buffer(add_m, join_style=2)
    return shapely.transform(expanded, to_wgs84, interleaved=False).bounds


def km_to_zoom(km: float) -> int:
    """
    Convert a desired tile side length (km) to the nearest integer zoom level.
    Uses the resolution at the equator (good enough for most global work).
    """
    tile_m = km * 1000.0
    zoom_float = math.log2(INITIAL_RESOLUTION * 256.0 / tile_m)
    return max(0, round(zoom_float))


def tile_to_coord(x: int, y: int, zoom: int, border_size_km: float = 0) -> (int, int, int, int):
    """
    Returns (west, south, east, north) in decimal degrees for the tile.
    """
    n = 2**zoom
    lon_deg_w = x / n * 360.0 - 180.0
    lon_deg_e = (x + 1) / n * 360.0 - 180.0

    def merc_y_to_lat(y_frac):
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y_frac)))
        return math.degrees(lat_rad)

    lat_deg_n = merc_y_to_lat(y / n)
    lat_deg_s = merc_y_to_lat((y + 1) / n)
    if border_size_km > 0:
        lon_deg_w, lat_deg_s, lon_deg_e, lat_deg_n = expand_bounding_box(
            lon_deg_w, lat_deg_s, lon_deg_e, lat_deg_n, border_size_km
        )
    return lon_deg_w, lat_deg_s, lon_deg_e, lat_deg_n


def coord_to_tile(lon: float, lat: float, zoom: int = ZOOM_1KM) -> (int, int):
    n = 2**zoom
    x = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(max(min(lat, 85.05112878), -85.05112878))
    y = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return int(x), int(y)


def get_tile_bounds(items: list[osmium.osm.Location], zoom: int):
    if not items:
        return None
    lon = (360, -360)
    lat = (360, -360)
    for loc in items:
        lon = (min(lon[0], loc.lon), max(lon[1], loc.lon))
        lat = (min(lat[0], loc.lat), max(lat[1], loc.lat))
    tx0, ty0 = coord_to_tile(lon[0], lat[0], zoom)
    tx1, ty1 = coord_to_tile(lon[1], lat[1], zoom)
    return (min(tx0, tx1), min(ty0, ty1), max(tx0, tx1), max(ty0, ty1))


def tiles_for_box(west, south, east, north, zoom):
    """
    Input bbox in EPSG:4326 (lon/lat). Returns inclusive ranges:
    (x_min, x_max, y_min, y_max)
    """
    x_min, y_max = coord_to_tile(west, north, zoom)  # note: north → y_max
    x_max, y_min = coord_to_tile(east, south, zoom)  # south → y_min
    # Clamp to valid tile indices
    max_index = 2**zoom - 1
    x_min = max(0, min(x_min, max_index))
    x_max = max(0, min(x_max, max_index))
    y_min = max(0, min(y_min, max_index))
    y_max = max(0, min(y_max, max_index))
    return x_min, x_max, y_min, y_max


def envelope_wkt(x: int, y: int, zoom: int, border_size_km: float = 0) -> str:
    """Return the tile envelope as a WKT POLYGON (used directly in DuckDB)."""
    lon_w, lat_s, lon_e, lat_n = tile_to_coord(x, y, zoom, border_size_km)
    return f"POLYGON(({lat_s} {lon_w}, {lat_n} {lon_w}, {lat_n} {lon_e}, {lat_s} {lon_e}, {lat_s} {lon_w}))"


def grid_fill(
    tile_size_km: float,
    border_size_km: float = 0,
    bounds: tuple[float, float, float, float] | None = None,
):
    """Fills an area with rectangles, from top-left to bottom-right with overlapping if needed."""
    zoom = km_to_zoom(tile_size_km)
    tiles_per_axis = 2**zoom
    x_min, x_max = 0, tiles_per_axis
    y_min, y_max = 0, tiles_per_axis
    if bounds:
        x_min, x_max, y_min, y_max = tiles_for_box(*bounds, zoom)

    def gen():
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                yield x, y, zoom

    return (x_max - x_min + 1) * (y_max - y_min + 1), gen()


def mapping_union(geoms: list[shapely.Geometry]) -> list[tuple[shapely.Geometry, list[int]]]:
    """
    Returns a list of (new_component, list_of_original_geometries_that_form_it)
    """
    if not geoms:
        return []

    unioned = shapely.unary_union(geoms)
    components = (
        unioned.geoms
        if unioned.geom_type == "GeometryCollection" or unioned.geom_type == "MultiPolygon"
        else [unioned]
    )

    if not components:
        return []

    tree = strtree.STRtree(geoms)
    return [
        (component, sorted(tree.query(component, predicate="intersects")))
        for component in components
    ]
