from collections.abc import Generator

import distort
import geom
import shapely
import subsets
import tilesource


def slice_tile(tile: tilesource.Tile) -> Generator[tilesource.Tile]:
    objects = [
        t
        for t in tile.objects
        if isinstance(t.geom, shapely.geometry.Polygon) and "building" in t.tags
    ]
    if objects:
        yield tilesource.Tile(tile.x, tile.y, tile.zoom, objects)


def slice(tile: Generator[tilesource.Tile]) -> Generator[tilesource.Tile]:
    for t in tile:
        yield from slice_tile(t)


def unite_tile(tile: tilesource.Tile) -> tilesource.Tile:
    united = geom.mapping_union([o.geom for o in tile.objects])
    objects = []
    for i, (component, originals) in enumerate(united):
        if len(originals) == 1:
            objects.append(tile.objects[originals[0]])
        else:
            objects.append(
                tilesource.UnitedOsmObject(
                    id=hex(hash(",".join(tile.objects[i].id for i in originals))),
                    tags={},
                    geom=component,
                    original=[tile.objects[i].id for i in originals],
                )
            )
    return tilesource.Tile(tile.x, tile.y, tile.zoom, objects)


def unite(tile: Generator[tilesource.Tile]) -> Generator[tilesource.Tile]:
    for t in tile:
        yield unite_tile(t)


def make_variants(tile: tilesource.Tile) -> Generator[tilesource.Tile]:
    distorted = [
        tilesource.OsmObject(tile.objects[i].id, tile.objects[i].tags, g)
        for i, g in enumerate(distort.distort_geoms([t.geom for t in tile.objects]))
    ]
    yield tilesource.Tile(tile.x, tile.y, tile.zoom, objects=distorted)
    if len(tile.objects) > 500:
        print("OOPS-VARIANTS", tile.x, tile.y, tile.zoom)
    for i, group in enumerate(subsets.get_neighbors([o.geom for o in tile.objects])):
        yield tilesource.Tile(tile.x, tile.y, tile.zoom, objects=[distorted[i] for i in group])


def variants(tile: Generator[tilesource.Tile]) -> Generator[tilesource.Tile]:
    for t in tile:
        yield from make_variants(t)
