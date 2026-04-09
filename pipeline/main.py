import argparse
import logging

import faiss
from matplotlib import patches
from matplotlib.path import Path
import shapely
import numpy as np

import features
import tilesource
import process

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate tile stream tiles from the database.")
    parser.add_argument("db_path", type=str, help="Path to the duckdb file with the tiles")
    parser.add_argument("target", type=str, help="Target where to dump the search index")
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

    baseTiles = tilesource.get_tiles(args.db_path, args.tile_size_km, bounds)
    sliced = process.slice(baseTiles)
    united = process.unite(sliced)
    variants = list(process.variants(united))

    quantizer = faiss.IndexFlatL2(features.VECTOR_LENGTH)
    index = faiss.IndexIDMap(quantizer)

    for i, tile in enumerate(variants):
        logger.info("tile %d/%d/%d has %d objects", tile.x, tile.y, tile.zoom, len(tile.objects))
        index.add_with_ids(np.array([features.vectorize(tile)]), np.array([i]))

    logger.info("saving index of %d vectors to %s", len(variants), args.target)
    faiss.write_index(index, args.target)
    logger.info("done.")
