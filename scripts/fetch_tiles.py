import io
import logging
import math
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
from PIL import Image

LAYER = os.environ.get("LAYER", "buildings")
TARGET = os.environ.get("TARGET", "./data/tiles")
TILESERVER = os.environ.get("TILESERVER", "http://localhost:8080")

TILE_SIZE = 512
EXT = "png"

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


def wgs84ToTile(lon: float, lat: float, zoom: int) -> (int, int):
    n = 2**zoom
    x = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(max(min(lat, 85.05112878), -85.05112878))
    y = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return int(x), int(y)


def tilesForBox(west, south, east, north, zoom):
    """
    Input bbox in EPSG:4326 (lon/lat). Returns inclusive ranges:
    (x_min, x_max, y_min, y_max)
    """
    x_min, y_max = wgs84ToTile(west, north, zoom)  # note: north → y_max
    x_max, y_min = wgs84ToTile(east, south, zoom)  # south → y_min
    # Clamp to valid tile indices
    max_index = 2**zoom - 1
    x_min = max(0, min(x_min, max_index))
    x_max = max(0, min(x_max, max_index))
    y_min = max(0, min(y_min, max_index))
    y_max = max(0, min(y_max, max_index))
    return x_min, x_max, y_min, y_max

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
nprocs = cpu_count()

def download_tile(z, x, y):
    url = f"{TILESERVER}/styles/{LAYER}/{TILE_SIZE}/{z}/{x}/{y}.{EXT}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    img.load()
    return img

def save_tile(x, y, zoom):
    targetDir = os.path.join(TARGET, str(zoom))
    targetImage = os.path.join(targetDir, f"{x}_{y}.png")
    tileId = f"zoom={zoom}, x={x}[{tileRange[1]}], y={y}[{tileRange[3]}]"
    if os.path.exists(targetImage):
        logger.info("Skipping tile %s to %s: already exists", tileId, targetImage)
        return
    logger.info("Downloading tile %s to %s", tileId, targetImage)
    tile = download_tile(zoom, x, y)
    extrema = tile.convert("L").getextrema()
    if extrema[0] == extrema[1]:
        logger.warning("Tile %s is empty", tileId)
    tile.save(targetImage)

bounds = {
    "lat": (8.410956391303783, 9.001454022020148),
    "lon": (47.168021083514404, 47.39871778943583)
}
topLeft = (47.54999199587565, 8.053970030592254)
bottomRight = (47.12671318268564, 9.114606132179778)
# topLeft = (45.7769477403, 6.02260949059)
# bottomRight = (47.8308275417, 10.4427014502)

logger.info("Fetching tiles")
for zoom in range(15, 19):
    tileRange = tilesForBox(
        min(*bounds["lat"]), max(*bounds["lon"]),
        max(*bounds["lat"]), min(*bounds["lon"]),
        zoom
    )
    logger.info("Fetcing tiles for zoom level %d: %s", zoom, tileRange)
    targetDir = os.path.join(TARGET, str(zoom))
    os.makedirs(targetDir, exist_ok=True)
    with ThreadPoolExecutor(max_workers=nprocs) as executor:
        for i, x in enumerate(range(tileRange[0], tileRange[1] + 1)):
            for j, y in enumerate(range(tileRange[2], tileRange[3] + 1)):
                executor.submit(save_tile, x, y, zoom)
        executor.shutdown(wait=True)