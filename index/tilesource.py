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


def from_db(
    db_path: str,
    tile_size_km: float,
    border_size_km: float = 0,
    bounds: tuple[float, float, float, float] | None = None,
) -> Generator[Tile]:
    zoom = geom.km_to_zoom(tile_size_km)
    total_tiles, tile_stream = geom.grid_fill(tile_size_km, border_size_km, bounds)
    logger.info(
        "generating tiles with side ~%.2fkm with ~%.2fkm border, zoom: %d, total tiles: %s",
        tile_size_km,
        border_size_km,
        zoom,
        total_tiles,
    )

    logger.info("loading OSM data from %s", db_path)
    conn = duckdb.connect(database=db_path, read_only=True)
    conn.execute("INSTALL spatial; LOAD spatial;")
    for i, tile in enumerate(tile_stream):
        x, y, zoom = tile
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
            "loaded tile %d of %d: %d/%d/%d with %d objects",
            i,
            total_tiles,
            x,
            y,
            zoom,
            len(objects),
        )
        yield Tile(x, y, zoom, objects)
