import argparse
import json
import collections
import logging
import time
from cProfile import Profile
from pstats import SortKey, Stats

import osmium
import geom

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TileCollector:

    def __init__(self):
        self._tiles = collections.defaultdict(list)
        self._seen = collections.defaultdict(int)
        self._profile = None

    def put(self, x: int, y: int, zoom: int, data):
        dtype = data["type"]
        self._seen[dtype] += 1
        if self._seen[dtype] % 100000 == 0:
            logger.info("parsed %d of %s", self._seen[dtype], dtype)
        if self._seen[dtype] % 1000000 == 0:
            Stats(self._profile).strip_dirs().sort_stats(SortKey.TIME).print_stats()
        # self._tiles[(x, y, zoom)] = data

    def save(self, target: str):
        with open(target, "w") as f:
            json.dump(self._tiles, f)


class TileExtractor(osmium.SimpleHandler):

    def __init__(self, collector: TileCollector):
        super().__init__()
        self._zoom = geom.ZOOM_1KM
        self._collector = collector
        self._cache = dict()
        self._seen = dict()

    def node(self, n):
        self._cache[n.id] = n
        tilexy = geom.wgs84ToTile(n.location.lon, n.location.lat, self._zoom)
        self._collector.put(
            tilexy[0],
            tilexy[1],
            self._zoom,
            {"id": n.id, "type": "node"},
        )

    def way(self, w):
        if not w.nodes:
            return
        self._cache[w.id] = w
        bounds = geom.get_tile_bounds(w.nodes, self._zoom)
        if not bounds:
            return
        for tx in range(bounds[0], bounds[2] + 1):
            for ty in range(bounds[1], bounds[3] + 1):
                self._collector.put(tx, ty, self._zoom, {"id": w.id, "type": "way"})

    def relation(self, r):
        real_members = []
        for mref in r.members:
            m = self._cache[mref]
            if isinstance(m, osmium.osm.Node):
                real_members.append(m)
            elif isinstance(m, osmium.osm.Way):
                real_members.extend(m.nodes)
        print ("REL")
        bounds = geom.get_tile_bounds(real_members, self._zoom)
        if not bounds:
            return
        for tx in range(bounds[0], bounds[2] + 1):
            for ty in range(bounds[1], bounds[3] + 1):
                self._collector.put(tx, ty, self._zoom, {"id": r.id, "type": "relation"})


def get_tiles(osm_file: str, tile_size_km: int):
    with Profile() as profile:
        collector = TileCollector()
        collector._profile = profile
        extractor = TileExtractor(collector)
        logger.info("loading OSM data from %s", osm_file)
        extractor.apply_file(osm_file, locations=True)
        logger.info("saving per-tile data to %s", "pertile.json")
        collector.save("pertile.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate tile stream tiles from .pbf file."
    )
    parser.add_argument("osm_file", type=str, help="Path to the OSM .pbf file")
    parser.add_argument("tile_size_km", type=float, help="Tile size in km (e.g., 10)")
    args = parser.parse_args()
    get_tiles(args.osm_file, args.tile_size_km)
