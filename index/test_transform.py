import random

import pytest
import shapely

import transform


def _ratio(x, y, x1, y1):
    return abs((x - x1) / (y - y1))


@pytest.mark.parametrize(
    "geom,bounds",
    [
        pytest.param(
            shapely.GeometryCollection(
                [shapely.Polygon([(1, 1), (3, 10), (5, 12), (10, 12), (8, 1), (1, 1)])]
            ),
            (0, 0, 1, 1),
            id="one_convex_polygon",
        ),
        pytest.param(
            shapely.GeometryCollection(
                [
                    shapely.Polygon([(1, 1), (3, 10), (5, 12), (10, 12), (8, 1), (1, 1)]),
                    shapely.Polygon([(15, 15), (15, 20), (20, 20), (20, 15), (15, 15)]),
                ]
            ),
            (0, 0, 1, 1),
            id="two_convex_polygons",
        ),
        pytest.param(
            shapely.GeometryCollection(
                [
                    shapely.Polygon([(1, 1), (3, 10), (5, 12), (10, 12), (8, 1), (1, 1)]),
                    shapely.Polygon([(10, 10), (15, 10), (15, 15), (10, 15), (10, 10)]),
                ]
            ),
            (0, 0, 1, 1),
            id="two_convex_intersecting",
        ),
    ],
)
def test_fit(geom, bounds):
    target = shapely.box(*bounds)
    orig_bounds = geom.bounds

    bounded = transform.fit(geom, (0, 0, 1, 1))
    assert target.contains(shapely.box(*bounded.bounds))

    bounded = transform.fit(geom, (0, 0, 1, 1), keep_aspect=True)
    assert _ratio(*bounded.bounds) == pytest.approx(_ratio(*geom.bounds))

    restored = transform.fit(bounded, orig_bounds, keep_aspect=True)
    assert restored.equals_exact(geom, tolerance=0.0001)
