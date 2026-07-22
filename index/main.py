import argparse
import logging
import pathlib
import time
from itertools import chain
from multiprocessing import Pool, cpu_count
from pathlib import Path

import shapely

import tilesource
import transform

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("main")


def slice(tile: tilesource.Tile) -> Iterable[tilesource.Tile]:
    objects = [
        t
        for t in tile.objects
        if isinstance(t.geom, shapely.geometry.Polygon) and "building" in t.tags
    ]
    if objects:
        return [tilesource.Tile(tile.x, tile.y, tile.zoom, objects)]
    return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate tile stream tiles from the database.")
    parser.add_argument("db_path", type=str, help="Path to the duckdb file with the tiles")
    parser.add_argument("--tile_size_km", type=float, help="Tile size in km (e.g., 10)")
    parser.add_argument(
        "--border_size_km", type=float, help="Border size in km (e.g., 1)", default=0
    )
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
        bounds = (min(*lons), max(*lats), max(*lons), min(*lats))
        logger.info("using bounds %s", bound_values)

    baseTiles = tilesource.from_db(args.db_path, args.tile_size_km, args.border_size_km, bounds)
    for i, tile in enumerate(chain.from_iterable(map(slice, baseTiles))):
        geoms = shapely.GeometryCollection([o.geom for o in tile.objects])
        obj = transform.fit(geoms, (0, 0, 1, 1), keep_aspect=True)
