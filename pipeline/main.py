import argparse
import logging

import matplotlib.pyplot as plt
from matplotlib import patches
from matplotlib.path import Path
import shapely

import tilesource
import process
import features

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("main")

def drawGeoms(ax, geoms, style='g'):
  for geom in geoms:
    if isinstance(geom, shapely.geometry.LineString):
      codes = [Path.MOVETO]
      for _ in geom.coords[1:]:
        codes.append(Path.LINETO)
      ax.add_patch(patches.PathPatch(Path(geom.coords, codes), facecolor='none', lw=2))
    else:
      ax.fill(*geom.exterior.xy, style)

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

    baseTiles = tilesource.get_tiles(args.db_path, args.tile_size_km, bounds)
    sliced = process.slice(baseTiles)
    variants = list(process.variants(sliced))
    hhu = features.moments_hu(variants[0].objects[0].geom)
    print(hhu)

    # for v in variants:
    #     logger.info("tile %d/%d/%d has %d objects", v.x, v.y, v.zoom, len(v.objects))
    # vars = variants[0:10]
    # fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(20, 20))
    # for i, t in enumerate(vars):
    #     drawGeoms(ax, [o.geom for o in t.objects], ['r', 'g', 'b'][ i % 3])
    # plt.show()

