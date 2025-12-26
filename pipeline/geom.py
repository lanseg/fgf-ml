import math
import osmium

ZOOM_1KM = 14

def tileToWgs84(x: int, y: int, zoom: int) -> (int, int, int, int):
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


def wgs84ToTile(lon: float, lat: float, zoom: int = ZOOM_1KM) -> (int, int):
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
    tx0, ty0 = wgs84ToTile(lon[0], lat[0], zoom)
    tx1, ty1 = wgs84ToTile(lon[1], lat[1], zoom)
    return (min(tx0, tx1), min(ty0, ty1), max(tx0, tx1), max(ty0, ty1))