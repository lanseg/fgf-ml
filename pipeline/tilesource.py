import argparse
import logging
import os

import geopandas as gpd
import duckdb

import geom

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROJ = "WGS84"


def save_tile(target, batch):

    for rbatch in batch:
        df = rbatch.to_pandas()
        gdf = gpd.GeoDataFrame(
            df.drop(columns=["geom"]), geometry=gpd.array.from_wkb(df["geom"], crs=PROJ)
        )
        gdf.to_file(target, driver="GeoJSON")


def get_tiles(
    db_path: str,
    target: str,
    tile_size_km: int,
    bounds: tuple[float, float, float, float] | None = None,
):
    zoom = geom.km_to_zoom(tile_size_km)
    tiles_per_axis = 2**zoom
    logger.info(
        "generating tiles with side ~%.2fkm, zoom: %d, tiles per axis: %s",
        tile_size_km,
        zoom,
        tiles_per_axis,
    )
    logger.info("loading OSM data from %s", db_path)
    conn = duckdb.connect(database=db_path, read_only=True)
    conn.execute("INSTALL spatial; LOAD spatial;")
    x_min, x_max = 0, tiles_per_axis
    y_min, y_max = 0, tiles_per_axis
    if bounds:
        x_min, x_max, y_min, y_max = geom.tiles_for_box(*bounds, zoom)

    if not os.path.exists(target):
        logger.info("creating target directory")
        os.makedirs(target, exist_ok=True)

    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            logger.info("fetching tile [%d, %d, %d]", x, y, zoom)
            envelope = geom.envelope_wkt(x, y, zoom)
            sql = """SELECT feature_id, ST_AsWKB(geometry) AS geom
                     FROM osm
                     WHERE ST_Intersects(geometry, ST_GeomFromText(?))"""
            batch = conn.execute(sql, (envelope,)).fetch_record_batch()
            save_tile(f"{target}/{x}_{y}_{zoom}.jsonl", batch)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate tile stream tiles from .pbf file.")
    parser.add_argument("db_path", type=str, help="Path to the OSM .pbf file")
    parser.add_argument("target", type=str, help="Target where to dump the tiles (only geojson for now)")
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

    get_tiles(args.db_path, args.target, args.tile_size_km, bounds)
