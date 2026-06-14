import argparse
import logging
import pathlib
import time
from itertools import chain
from multiprocessing import Pool, cpu_count

import augment
import features
import storage
import tilesource

BATCH_SIZE = 10000

nproc = cpu_count() - 2 if cpu_count() > 4 else 1

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("main")


def pipeline(src: tilesource.Tile) -> list[features.FeatureVector]:
    start = time.time()
    sliced = augment.slice(src)
    united = map(augment.unite_tile, sliced)
    variants = map(augment.variants, united)
    vectors = list(map(features.vectorizeTile, chain.from_iterable(variants)))
    duration = time.time() - start
    logger.info(
        "tile (%d, %d, %d) processed in %.2f seconds. Generated %d vectors from %d objects.",
        src.x,
        src.y,
        src.zoom,
        duration,
        len(vectors),
        len(src.objects),
    )
    return vectors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate tile stream tiles from the database.")
    parser.add_argument("db_path", type=str, help="Path to the duckdb file with the tiles")
    parser.add_argument("index", type=str, help="Target where to dump the search index")
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
        bounds = (min(*lats), max(*lons), max(*lats), min(*lons))
        logger.info("using bounds %s", bound_values)

    index = storage.Storage(pathlib.Path(args.index), features.VECTOR_LENGTH)
    with Pool(nproc) as p:
        baseTiles = tilesource.get_tiles(
            args.db_path, args.tile_size_km, args.border_size_km, bounds
        )
        vectors = p.imap_unordered(
            pipeline, filter(lambda x: x.objects, baseTiles))
        for i, fv in enumerate(chain.from_iterable(vectors)):
            index.add(i, fv)

    index.flush()
