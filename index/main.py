import argparse
import logging
import pathlib
import time
from itertools import batched, chain
from multiprocessing import Pool, cpu_count
from pathlib import Path
import atexit
import sys
import faulthandler
import tracemalloc

import cv2
import numpy as np
import shapely
from PIL import Image

import augment
import clip
import geom
import storage
import tilesource
import transform

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("main")

img_size = 224
clip_batch_size = 128
nproc = min(16, max(1, cpu_count() - 2))


def rasterize_tile(tile, img_size=224):
    geoms = shapely.GeometryCollection([o.geom for o in tile.objects])
    obj = transform.fit(geoms, (0, 0, img_size, img_size), keep_aspect=True)
    return clip.rasterize_geometry(obj.geoms)


def init_worker():
    faulthandler.enable(all_threads=True)
    sys.stdout.reconfigure(line_buffering=True)
    tracemalloc.start(10)

    # Store the baseline snapshot at process start
    global _baseline
    _baseline = tracemalloc.take_snapshot()

def exit_worker():
    if tracemalloc.is_tracing():
        current = tracemalloc.take_snapshot()
        diff = current.compare_to(_baseline, "lineno")
        log.info("=== Memory delta for this worker process ===")
        for stat in diff[:15]:
            log.info(str(stat))

def pipeline(baseTile: tilesource.Tile) -> list[tilesource.Tile]:
    start = time.time()
    sliced = tilesource.slice_by_type(baseTile)
    buildings = filter(lambda tile: "building" in tile.objects[0].tags, sliced)
    united = map(augment.unite_tile, buildings)
    variants = list(chain.from_iterable(map(augment.variants, united)))
    aug_time = time.time()
    result = [(v, rasterize_tile(v, img_size)) for v in variants]
    raster_time = time.time()
    logger.info(
        "Processed tile %s in %d seconds: variants=%d, aug_time=%d, raster_time=%d",
        baseTile,
        raster_time - start,
        len(variants),
        aug_time - start,
        raster_time - aug_time,
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate tile stream tiles from the database.")
    parser.add_argument("db_path", type=str, help="Path to the duckdb file with the tiles")
    parser.add_argument("--tile_size_km", type=float, help="Tile size in km (e.g., 10)")
    parser.add_argument(
        "--border_size_km", type=float, help="Border size in km (e.g., 1)", default=0
    )
    parser.add_argument("index", type=str, help="Target where to dump the search index")
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

    generator = clip.CLIPEmbeddingGenerator()
    index = storage.Storage(pathlib.Path(args.index), 512)

    with Pool(nproc, initializer=init_worker) as p:
        baseTiles = tilesource.from_db(args.db_path, args.tile_size_km, args.border_size_km, bounds)
        atexit.register(exit_worker)

        i = 0
        for batch in batched(
            chain.from_iterable(p.imap_unordered(pipeline, filter(lambda x: x.objects, baseTiles))),
            clip_batch_size,
        ):
            tiles, imgs = list(zip(*batch))
            start = time.time()
            embs = generator.generate_batch_embeddings(imgs)
            for tile, emb in zip(tiles, embs):
                index.add(i, storage.TileEmbedding(tile=(tile.x, tile.y, tile.zoom), vector=emb))
                i += 1
            emb_time = time.time()
            logger.info(
                "generated %d (%d total) embeddings in %ds for tiles: %s... %s",
                len(embs),
                i,
                emb_time - start,
                tiles[0],
                tiles[-1]
            )
    index.flush()
