import math
import osmium

ZOOM_1KM = 14
WEB_MERCATOR_RADIUS = 6378137.0
WEB_MERCATOR_MAX = WEB_MERCATOR_RADIUS * math.pi  # ≈ 20037508.342789244
INITIAL_RESOLUTION = (
    2 * math.pi * WEB_MERCATOR_RADIUS / 256.0
)  # ≈ 156543.033928041 (metres/pixel at zoom 0)


def km_to_zoom(km: float) -> int:
    """
    Convert a desired tile side length (km) to the nearest integer zoom level.
    Uses the resolution at the equator (good enough for most global work).
    """
    tile_m = km * 1000.0
    zoom_float = math.log2(INITIAL_RESOLUTION * 256.0 / tile_m)
    return max(0, round(zoom_float))


def tile_to_wgs84(x: int, y: int, zoom: int) -> (int, int, int, int):
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
    return lon_deg_w, lat_deg_s, lon_deg_e, lat_deg_n


def wgs84_to_tile(lon: float, lat: float, zoom: int = ZOOM_1KM) -> (int, int):
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
    tx0, ty0 = wgs84_to_tile(lon[0], lat[0], zoom)
    tx1, ty1 = wgs84_to_tile(lon[1], lat[1], zoom)
    return (min(tx0, tx1), min(ty0, ty1), max(tx0, tx1), max(ty0, ty1))


def tiles_for_box(west, south, east, north, zoom):
    """
    Input bbox in EPSG:4326 (lon/lat). Returns inclusive ranges:
    (x_min, x_max, y_min, y_max)
    """
    x_min, y_max = wgs84_to_tile(west, north, zoom)  # note: north → y_max
    x_max, y_min = wgs84_to_tile(east, south, zoom)  # south → y_min
    # Clamp to valid tile indices
    max_index = 2**zoom - 1
    x_min = max(0, min(x_min, max_index))
    x_max = max(0, min(x_max, max_index))
    y_min = max(0, min(y_min, max_index))
    y_max = max(0, min(y_max, max_index))
    return x_min, x_max, y_min, y_max


def envelope_wkt(x: int, y: int, zoom: int) -> str:
    """Return the tile envelope as a WKT POLYGON (used directly in DuckDB)."""
    xmin, ymin, xmax, ymax = tile_to_wgs84(x, y, zoom)
    return f"POLYGON(({xmin} {ymin}, {xmax} {ymin}, {xmax} {ymax}, {xmin} {ymax}, {xmin} {ymin}))"
