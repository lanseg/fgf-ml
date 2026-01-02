import argparse
import logging

import tilesource

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("main")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate tile stream tiles from .pbf file.")
    parser.add_argument("db_path", type=str, help="Path to the OSM .pbf file")
    parser.add_argument(
        "target", type=str, help="Target where to dump the tiles (only geojson for now)"
    )
    parser.add_argument("--tile_size_km", type=float, help="Tile size in km (e.g., 10)")
    parser.add_argument(
        "--bounds",
        help="Region bounds as four comma-separated floats: lon,lat,lon,lat",
    )
    args = parser.parse_args()

    bounds = None
    if args.bounds:
        bound_values = list(map(float, args.bounds.split(",")))
        lons = [bound_values[0], bound_values[2]]
        lats = [bound_values[1], bound_values[3]]
        bounds = (min(*lats), max(*lons), max(*lats), min(*lons))
        logger.info("using bounds %s", bound_values)

    for tile in tilesource.get_tiles(args.db_path, args.target, args.tile_size_km, bounds):
        logger.info(
            "tile [x=%d, y=%d, zoom=%d]: %d geoms", tile.x, tile.y, tile.zoom, len(tile.objects)
        )
