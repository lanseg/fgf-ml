import argparse
import logging
import pathlib
import time
from itertools import chain
from multiprocessing import Pool, cpu_count
from pathlib import Path

import numpy as np
import shapely

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
nproc = cpu_count() - 2 if cpu_count() > 4 else 1


def pipeline(baseTile: tilesource.Tile) -> list[tilesource.Tile]:
    start = time.time()
    sliced = tilesource.slice_by_type(baseTile)
    buildings = filter(lambda tile: "building" in tile.objects[0].tags, sliced)
    united = map(augment.unite_tile, buildings)
    variants = chain.from_iterable(map(augment.variants, united))
    return list(variants)


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
    clip_batch_size = 128

    with Pool(nproc) as p:
        baseTiles = tilesource.from_db(args.db_path, args.tile_size_km, args.border_size_km, bounds)

        i = 0
        images = []

        for batch in p.imap_unordered(pipeline, filter(lambda x: x.objects, baseTiles)):
            for tile in batch:
                geoms = shapely.GeometryCollection([o.geom for o in tile.objects])
                obj = transform.fit(geoms, (0, 0, img_size, img_size), keep_aspect=True)
                images.append((tile, generator.rasterize_geometry(obj.geoms, img_size)))

            while len(images) > clip_batch_size:
                img_batch, images = images[:clip_batch_size], images[clip_batch_size:]
                embs = generator.generate_batch_embeddings([i[1] for i in img_batch])
                for idx, emb in enumerate(embs):
                    tile = img_batch[idx][0]
                    te = storage.TileEmbedding(tile=(tile.x, tile.y, tile.zoom), vector=emb)
                    index.add(i, te)
                    i += 1
                logger.info(
                    "processed %d tile variants (%d per batch, %d remaining)",
                    i,
                    clip_batch_size,
                    len(images),
                )

        if len(images) > 0:
            img_batch, images = images[:clip_batch_size], images[clip_batch_size:]
            embs = generator.generate_batch_embeddings([i[1] for i in img_batch])
            for idx, emb in enumerate(embs):
                tile = img_batch[idx][0]
                te = storage.TileEmbedding(tile=(tile.x, tile.y, tile.zoom), vector=emb)
                index.add(i, te)
                i += 1
            logger.info(
                "processed %d tile variants (%d per batch, %d remaining)",
                i,
                clip_batch_size,
                len(images),
            )
    index.flush()
