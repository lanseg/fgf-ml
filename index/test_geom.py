import random

import pytest
import shapely

import geom

_boxes = [
    # Prime  | Equator
    (8.535862, 47.378912, 8.544016, 47.382457),  # Before | Above
    (-0.01, 47.378912, 0.01, 47.382457),  # Cross  | Above
    (-8.544016, 47.378912, -8.535862, 47.382457),  # After  | Above
    (8.535862, 0.01, 8.544016, -0.01),  # Before | Cross
    (-0.01, 0.01, 0.01, -0.01),  # Cross  | Cross
    (-8.544016, 0.01, -8.535862, -0.01),  # After  | Cross
    (8.535862, -47.382457, 8.544016, -47.378912),  # Before | Below
    (-0.01, -47.382457, 0.01, -47.378912),  # Cross  | Below
    (-8.544016, -47.382457, -8.535862, -47.378912),  # After  | Below
]

# Lon Lat
_zurich_hb = (8.53976, 47.37795)
_switzerland = (5.4467010850356266, 47.73248844856869, 11.4152400783939, 45.864502976445976)


@pytest.mark.parametrize("box", _boxes)
def test_expand_bounding_box(box):
    west, south, east, north = geom.expand_bounding_box(*box, 1000)

    lon1, lat1, lon2, lat2 = box

    # Antimeridian case needs special handling.
    if lon1 > lon2:
        assert west > east
        assert south < min(lat1, lat2)
        assert north > max(lat1, lat2)
    else:
        assert west < min(lon1, lon2)
        assert east > max(lon1, lon2)
        assert south < min(lat1, lat2)
        assert north > max(lat1, lat2)


def test_coord_tile():
    zoom = 6
    lon, lat = _zurich_hb
    tile = geom.coord_to_tile(lon, lat, zoom)  # Forward
    (west, south, east, north) = geom.tile_to_coord(tile[0], tile[1], zoom)  # Inverse
    assert lon < east and lon > west
    assert lat < north and lat > south

    for _ in range(10):
        rand_lat = lat + random.uniform(-0.1, 0.1)
        rand_lon = lon + random.uniform(-0.1, 0.1)
        assert geom.coord_to_tile(rand_lon, rand_lat, zoom) == tile


@pytest.mark.parametrize(
    "tile_size,bounds",
    [
        (10, _switzerland),
        (100, _switzerland),
        (3000, _switzerland),
        (10, _switzerland),
        (100, _switzerland),
        (3000, _switzerland),
    ],
)
def test_grid_fill(tile_size, bounds):
    bound_box = shapely.box(*bounds)
    count, it = geom.grid_fill(tile_size, bound_box)
    coverage = []
    for x, y, zoom in it:
        coverage.append(shapely.box(*geom.tile_to_coord(x, y, zoom)))
    assert bound_box.area == shapely.unary_union(coverage).intersection(bound_box).area
