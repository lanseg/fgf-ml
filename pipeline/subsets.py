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


def get_neighbors(geoms: list[Geometry]) -> list[tuple[int, ...]]:
    centroids = [_xy(centroid(g)) for g in geoms]
    tri = Delaunay(centroids)
    grouped = collections.defaultdict(set)
    for s in tri.simplices:
        s = list(map(int, s))
        grouped[s[0]].update([s[1], s[2]])
        grouped[s[1]].update([s[0], s[2]])
        grouped[s[2]].update([s[1], s[0]])
    return list(
        set(
            tuple(sorted(subgroup))
            for root, other in grouped.items()
            for subgroup in _powerset({root} | other)
        )
    )
