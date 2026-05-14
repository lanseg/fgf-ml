import numpy as np
import cv2

import shapely
import transform
import tilesource

# Number of objects + 7 Hu moments
VECTOR_LENGTH = 8


def _hu(geoms: list[shapely.Geometry], image_size=128):
    """Calculate hu moments for the normalized ([-1, -1]) list of geometries."""

    mask = np.zeros((image_size, image_size), dtype=np.uint8)

    # Transform geometries from [-1, 1] to [0, image_size]
    def transform_coords(x, y):
        px = (x + 1) / 2 * (image_size - 1)
        py = (y + 1) / 2 * (image_size - 1)
        return int(px), int((image_size - 1) - py)

    for geom in geoms:
        if geom.is_empty or not hasattr(geom, "exterior"):
            continue

        coords = list(geom.exterior.coords)
        pixel_coords = [transform_coords(x, y) for x, y in coords]

        pts = np.array(pixel_coords, np.int32)
        cv2.fillPoly(mask, [pts], 255)

        for interior in geom.interiors:
            hole_coords = [transform_coords(x, y) for x, y in interior.coords]
            hole_pts = np.array(hole_coords, np.int32)
            cv2.fillPoly(mask, [hole_pts], 0)

    hu_moments = cv2.HuMoments(cv2.moments(mask)).flatten()

    for i in range(0, 7):
        if hu_moments[i] != 0:
            hu_moments[i] = -1 * np.sign(hu_moments[i]) * np.log10(np.abs(hu_moments[i]))
        else:
            hu_moments[i] = 0
    return hu_moments


def vectorizeTile(tile: tilesource.Tile):
    return (
        (tile.x, tile.y, tile.zoom, len(tile.objects)),
        vectorizeGeom([o.geom for o in tile.objects]),
    )


def vectorizeGeom(geoms: list[shapely.Geometry]):
    polygons = [
        geom
        for geom in geoms
        if isinstance(geom, shapely.geometry.Polygon)
        or isinstance(geom, shapely.geometry.MultiPolygon)
    ]
    gc = shapely.geometry.GeometryCollection(polygons)

    # Normalizing
    gc = transform.fit(gc, (-1, -1, 1, 1))
    return np.concatenate([[len(polygons)], _hu(gc.geoms)])
