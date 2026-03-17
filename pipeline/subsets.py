import collections

from scipy.spatial import Delaunay
from shapely import Geometry, Point, centroid


def _xy(p: Point) -> (float, float):
    return p.x, p.y

def group_neighbors(geoms: list[Geometry]) -> dict[int, set[int]]:
    centroids = [_xy(centroid(g)) for g in geoms]
    tri = Delaunay(centroids)
    grouped = collections.defaultdict(set)
    for s in tri.simplices:
        s = list(map(int, s))
        grouped[s[0]].update([s[1], s[2]])
        grouped[s[1]].update([s[0], s[2]])
        grouped[s[2]].update([s[1], s[0]])
    return grouped