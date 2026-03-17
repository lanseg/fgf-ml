from collections.abc import Generator

import distort
import shapely
import tilesource


def slice_tile(tile: tilesource.Tile) -> Generator[tilesource.Tile]:
    objects = [
        t
        for t in tile.objects
        if isinstance(t.geom, shapely.geometry.Polygon) and "building" in t.tags
    ]
    yield tilesource.Tile(tile.x, tile.y, tile.zoom, objects)


def slice(tile: Generator[tilesource.Tile]) -> Generator[tilesource.Tile]:
    for t in tile:
        yield from slice_tile(t)


def make_variants(tile: tilesource.Tile) -> Generator[tilesource.Tile]:
    distorted = list(distort.distort_geoms([t.geom for t in tile.objects]))
    yield tilesource.Tile(
        tile.x,
        tile.y,
        tile.zoom,
        objects=[
            tilesource.OsmObject(tile.objects[i].id, tile.objects[i].tags, g)
            for i, g in enumerate(distorted)
        ],
    )


def variants(tile: Generator[tilesource.Tile]) -> Generator[tilesource.Tile]:
    for t in tile:
        yield from make_variants(t)
