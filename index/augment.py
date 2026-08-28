import collections
import logging
from collections.abc import Iterable
from itertools import chain, combinations

import shapely
from scipy.spatial import Delaunay
from shapely import Geometry, Point, centroid

import geom
import tilesource

logger = logging.getLogger("augment")


def _xy(p: Point) -> (float, float):
    return p.x, p.y


def _powerset(iterable):
    s = list(iterable)
    powerset = list(chain.from_iterable(combinations(s, r) for r in range(1, len(s) + 1)))
    return powerset


def _triangulate(points: list[tuple[float, float]]) -> list[tuple[int, set[int]]]:
    tri = Delaunay(points)
    grouped = collections.defaultdict(set)
    for i, j, k in tri.simplices:
        grouped[i] |= {j, k}
        grouped[j] |= {i, k}
        grouped[k] |= {i, j}
    return sorted(grouped.items())


def get_neighbors(geoms: list[Geometry]) -> list[tuple[int, ...]]:
    if len(geoms) < 4:
        return _powerset(range(len(geoms)))
    grouped = _triangulate([_xy(centroid(g)) for g in geoms])
    return list(
        set(
            tuple(sorted(subgroup))
            for root, other in grouped
            for subgroup in _powerset({root} | other)
        )
    )


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
    if len(tile.objects) > 500:
        logger.warning(
            "too many variants for tile at [%d/%d/%d]: %d",
            tile.x,
            tile.y,
            tile.zoom,
            len(tile.objects),
        )
    result = [tilesource.Tile(tile.x, tile.y, tile.zoom, objects=tile.objects)] + [
        tilesource.Tile(tile.x, tile.y, tile.zoom, objects=[tile.objects[i] for i in group])
        for group in get_neighbors([o.geom for o in tile.objects])
        if len(group) < 4
    ]
    logger.info(
        "generated %d variants for tile: %d/%d/%d with %d objects",
        len(result),
        tile.x,
        tile.y,
        tile.zoom,
        len(tile.objects),
    )
    return result
