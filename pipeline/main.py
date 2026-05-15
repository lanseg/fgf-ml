import argparse
import json
import logging
from itertools import chain

import faiss
from matplotlib import patches
from matplotlib.path import Path
import shapely
import numpy as np
from multiprocessing import cpu_count, pool

import features
import tilesource
import augment


nproc = cpu_count()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("main")


def drawGeoms(ax, geoms, style="g"):
    for geom in geoms:
        if isinstance(geom, shapely.geometry.LineString):
            codes = [Path.MOVETO]
            for _ in geom.coords[1:]:
                codes.append(Path.LINETO)
            ax.add_patch(patches.PathPatch(Path(geom.coords, codes), facecolor="none", lw=2))
        elif isinstance(geom, shapely.geometry.MultiPolygon):
            for poly in geom.geoms:
                ax.fill(*poly.exterior.xy, style)
        elif isinstance(geom, shapely.geometry.Polygon):
            ax.fill(*geom.exterior.xy, style)

def pipeline(src: tilesource.Tile) -> list[tuple[tuple[int, int, int, int], np.ndarray]]:
    sliced = augment.slice(src)
    united = map(augment.unite_tile, sliced)
    variants = map(augment.variants, united)
    vectors = list(map(features.vectorizeTile, chain.from_iterable(variants)))
    return list(vectors)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate tile stream tiles from the database.")
    parser.add_argument("db_path", type=str, help="Path to the duckdb file with the tiles")
    parser.add_argument("index", type=str, help="Target where to dump the search index")
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

    quantizer = faiss.IndexFlatL2(features.VECTOR_LENGTH)
    index = faiss.IndexIDMap(quantizer)

    id_to_tile = []
    with pool.Pool(nproc) as p:
        baseTiles = tilesource.get_tiles(args.db_path, args.tile_size_km, bounds)
        vectors = p.imap_unordered(pipeline, baseTiles)

        for i, ((x, y, z, n), v) in enumerate(chain.from_iterable(vectors)):
            logger.info("tile %d at %d/%d/%d has %d objects", i, x, y, z, n)
            index.add_with_ids(np.array([v]), np.array([i]))
            id_to_tile.append((x, y, z))

    logger.info("saving index of %d vectors to %s", index.ntotal, args.index)
    faiss.write_index(index, args.index)
    with open(f"{args.index}.metadata", "w") as index_metadata:
        json.dump(id_to_tile, index_metadata)
    logger.info("done.")
