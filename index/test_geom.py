import random

import pytest
import shapely

import geom

# def km_to_zoom(km: float) -> int:
# def tile_to_wgs84(x: int, y: int, zoom: int, border_size_km: float = 0) -> (int, int, int, int):
#     def merc_y_to_lat(y_frac):
# def wgs84_to_tile(lon: float, lat: float, zoom: int = ZOOM_1KM) -> (int, int):
# def get_tile_bounds(items: list[osmium.osm.Location], zoom: int):
# def tiles_for_box(west, south, east, north, zoom):
# def envelope_wkt(x: int, y: int, zoom: int, border_size_km: float = 0) -> str:
# def mapping_union(geoms: list[shapely.Geometry]) -> list[tuple[shapely.Geometry, list[int]]]:

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


def test_expand_bounding_box():
    deltas = []
    for box in _boxes:
        lon1, lat1, lon2, lat2 = box
        before = shapely.box(*box)
        after = shapely.box(*geom.expand_bounding_box(*box, 5000))
        deltas.append(round(100 * (after.length - before.length)))
    assert min(deltas) == max(deltas)
    assert deltas[0] > 0


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
    "tile_size,border_size_km,bounds",
    [
        (10, 0, _switzerland),
        (100, 0, _switzerland),
        (3000, 0, _switzerland),
        (10, 5, _switzerland),
        (100, 5, _switzerland),
        (3000, 5, _switzerland),
    ],
)
def test_grid_fill(tile_size, border_size_km, bounds):
    bound_box = shapely.box(*bounds)
    count, it = geom.grid_fill(tile_size, border_size_km, bounds)
    coverage = []
    for x, y, zoom in it:
        coverage.append(shapely.box(*geom.tile_to_coord(x, y, zoom)))
    assert bound_box.area == shapely.unary_union(coverage).intersection(bound_box).area
