import logging
from collections.abc import Iterable

import shapely

import distort
import geom
import subsets
import tilesource

logger = logging.getLogger("process")


def slice(tile: tilesource.Tile) -> Iterable[tilesource.Tile]:
    objects = [
        t
        for t in tile.objects
        if isinstance(t.geom, shapely.geometry.Polygon) and "building" in t.tags
    ]
    if objects:
        return [tilesource.Tile(tile.x, tile.y, tile.zoom, objects)]
    return []


def unite_tile(tile: tilesource.Tile) -> tilesource.Tile:
    objects = []
    for component, originals in geom.mapping_union([o.geom for o in tile.objects]):
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


def variants(tile: tilesource.Tile) -> Iterable[tilesource.Tile]:
    distorted = [
        tilesource.OsmObject(tile.objects[i].id, tile.objects[i].tags, g)
        for i, g in enumerate(distort.distort_geoms([t.geom for t in tile.objects]))
    ]
    if len(tile.objects) > 500:
        logger.warning(
            "too many variants for tile at [%d/%d/%d]: %d",
            tile.x,
            tile.y,
            tile.zoom,
            len(tile.objects),
        )
    return [tilesource.Tile(tile.x, tile.y, tile.zoom, objects=distorted)] + [
        tilesource.Tile(tile.x, tile.y, tile.zoom, objects=[distorted[i] for i in group])
        for group in subsets.get_neighbors([o.geom for o in tile.objects])
    ]
