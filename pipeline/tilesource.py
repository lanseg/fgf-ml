from collections.abc import Generator
from dataclasses import dataclass
import logging

from shapely import Geometry
import geopandas as gpd
import duckdb

import geom

logger = logging.getLogger(__name__)
PROJ = "WGS84"


@dataclass
class OsmObject:
    id: str
    tags: dict[str, str]
    geom: Geometry


@dataclass
class Tile:
    x: int
    y: int
    zoom: int
    objects: list[OsmObject]


def get_tiles(
    db_path: str,
    tile_size_km: float,
    bounds: tuple[float, float, float, float] | None = None,
) -> Generator[Tile]:
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

    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            logger.info("fetching tile [%d, %d, %d]", x, y, zoom)
            envelope = geom.envelope_wkt(x, y, zoom)
            sql = """SELECT feature_id, ST_AsWKB(geometry) AS geom, tags
                     FROM osm
                     WHERE ST_Intersects(geometry, ST_GeomFromText(?))"""
            batch = conn.execute(sql, (envelope,)).fetch_record_batch()
            objects = []
            for rbatch in batch:
                df = rbatch.to_pandas()
                df["geom"] = gpd.array.from_wkb(df["geom"], crs=PROJ)
                for tuple in df.itertuples():
                    objects.append(OsmObject(id=tuple[1], geom=tuple[2], tags=dict(tuple[3])))
            yield Tile(x, y, zoom, objects)
