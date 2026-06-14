import logging
from collections.abc import Generator
from dataclasses import dataclass

import duckdb
import geopandas as gpd
from shapely import Geometry

import geom

logger = logging.getLogger(__name__)
PROJ = "WGS84"


@dataclass
class OsmObject:
    id: str
    tags: dict[str, str]
    geom: Geometry


@dataclass
class UnitedOsmObject(OsmObject):
    original: list[str]


@dataclass
class Tile:
    x: int
    y: int
    zoom: int
    objects: list[OsmObject]


def get_tiles(
    db_path: str,
    tile_size_km: float,
    border_size_km: float = 0,
    bounds: tuple[float, float, float, float] | None = None,
) -> Generator[Tile]:
    zoom = geom.km_to_zoom(tile_size_km)
    tiles_per_axis = 2**zoom
    logger.info(
        "generating tiles with side ~%.2fkm with ~%.2fkm border, zoom: %d, tiles per axis: %s",
        tile_size_km,
        border_size_km,
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

    total_tiles = (x_max - x_min + 1) * (y_max - y_min + 1)
    tile_count = 0
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            envelope = geom.envelope_wkt(x, y, zoom, border_size_km)
            sql = """SELECT feature_id, ST_AsWKB(geometry) AS geom, tags
                     FROM osm
                     WHERE ST_Intersects(geometry, ST_GeomFromText(?))"""
            batch = conn.execute(sql, (envelope,)).fetch_record_batch()
            objects = []
            for rbatch in batch:
                df = rbatch.to_pandas()
                df["geom"] = gpd.array.from_wkb(df["geom"], crs=PROJ)
                for row in df.itertuples():
                    objects.append(OsmObject(id=row[1], geom=row[2], tags=dict(row[3])))
            logger.info(
                "loaded tile %d of %d: %d[%d]/%d[%d]/%d with %d objects",
                tile_count,
                total_tiles,
                x,
                x_max,
                y,
                y_max,
                zoom,
                len(objects),
            )
            tile_count += 1
            yield Tile(x, y, zoom, objects)
