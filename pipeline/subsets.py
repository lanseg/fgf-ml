import collections
from itertools import combinations, chain
from scipy.spatial import Delaunay
from shapely import Geometry, Point, centroid


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
