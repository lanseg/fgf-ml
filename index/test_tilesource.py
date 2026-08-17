import random

import pytest
import shapely

import tilesource


@pytest.mark.parametrize(
    "tile,expect",
    [
        (10, 0, _switzerland),
        (100, 0, _switzerland),
        (3000, 0, _switzerland),
        (10, 5, _switzerland),
        (100, 5, _switzerland),
        (3000, 5, _switzerland),
    ],
)
def test_filter_buildings(tile, expect):
    result = tilesource.slice(tile)
    pass
