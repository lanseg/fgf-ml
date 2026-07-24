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

def slicer(tile: tilesource.Tile) -> Iterable[Tile]:
    key = lambda obj: "building" if isinstance(obj.geom, shapely.Polygon) and "building" in obj.tags else None
    return tilesource.slice(tile, key)
    

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
    sliced = chain.from_iterable(map(slicer, baseTiles))
    buildings = filter(lambda tile: "building" in tile.objects[0].tags, sliced)

    for i, tile in enumerate(buildings):
        geoms = shapely.GeometryCollection([o.geom for o in tile.objects])
        obj = transform.fit(geoms, (0, 0, 1, 1), keep_aspect=True)
