from collections.abc import Generator

import shapely

import transform
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
    for g in transform.variants(shapely.GeometryCollection([t.geom for t in tile.objects])):
        yield tilesource.Tile(
            tile.x,
            tile.y,
            tile.zoom,
            objects=[
                tilesource.OsmObject(tile.objects[i].id, tile.objects[i].tags, g.geoms[i])
                for i in range(len(tile.objects))
            ],
        )


def variants(tile: Generator[tilesource.Tile]) -> Generator[tilesource.Tile]:
    for t in tile:
        yield from make_variants(t)
