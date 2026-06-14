from dataclasses import dataclass

import numpy as np
import shapely

import tilesource
import transform


@dataclass
class FeatureVector:
    tile: tuple[int, int, int, int]
    vector: np.ndarray


def toPointArray(geoms: shapely.GeometryCollection, sample_points=128):
    if not isinstance(geoms, shapely.GeometryCollection):
      geoms = shapely.GeometryCollection(geoms)
    coords = []
    for geom in geoms.geoms:
        if geom.is_empty:
            continue
        if isinstance(geom, shapely.Polygon):
            coords.extend(geom.exterior.coords)
        boundary = geom.boundary
        for i in np.linspace(0, 1, sample_points, endpoint=True):
            pt = boundary.interpolate(i, normalized=True)
            coords.append((pt.x, pt.y))
    return np.array(coords)

def radialDistanceHistogram(obj: list[shapely.Geometry], bins = 10, sp=20):
  pts = toPointArray(obj, sample_points=sp)
  gc = shapely.GeometryCollection(obj).centroid
  ctr = [gc.x, gc.y]
  counts, bins = np.histogram(
      [np.hypot(pt[0] - ctr[0], pt[1] - ctr[1]) for pt in pts],
      bins)
  return counts

def areaToHull(obj: list[shapely.Geometry]):
  gc = shapely.GeometryCollection(obj)
  return [gc.area / gc.convex_hull.area if gc.convex_hull.area > 0 else 0]

def norm(a):
  return (a - a.mean()) / (a.max() - a.min())

def eccentricity(geoms: shapely.GeometryCollection) -> float:
    coords = toPointArray(geoms)
    if len(coords) < 2:
        return 0.0
    cov = np.cov(coords, rowvar=False)
    eigenvalues, _ = np.linalg.eig(cov)
    if np.any(eigenvalues <= 0):
        return 0.0
    return np.sqrt(1 - min(eigenvalues) / max(eigenvalues))

VECTOR_LENGTH = 11

def vectorizeGeom(geoms: list[shapely.Geometry]) -> np.ndarray:
    polygons = [
        geom
        for geom in geoms
        if isinstance(geom, shapely.Polygon)
        or isinstance(geom, shapely.MultiPolygon)
    ]
    gc = shapely.GeometryCollection(polygons)

    methods = [
        lambda x: norm(radialDistanceHistogram(x, bins=10, sp=20)),
        lambda x: [areaToHull(x)[0] - 0.5]
    ]

    obj = transform.fit(gc, (-1, -1, 1, 1), keep_aspect=True)
    result = []
    for m in methods:
        result.extend(m(obj))
    assert len(result) == VECTOR_LENGTH, f"Expected length {VECTOR_LENGTH}, got {len(result)}"
    return np.array(result)

def vectorizeTile(tile: tilesource.Tile) -> FeatureVector:
    return FeatureVector(
        tile=(tile.x, tile.y, tile.zoom, len(tile.objects)),
        vector=vectorizeGeom([o.geom for o in tile.objects]),
    )