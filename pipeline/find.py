import argparse
import collections
import json
import logging
from pathlib import Path

import faiss
import numpy as np
from shapely.geometry import shape

import features
import geom

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("find")


def find_in_file(index_file: Path, vec: np.ndarray, top_k: int):
    logger.info("loading vector index from %s", index_file)
    index = faiss.read_index(str(index_file))
    logger.info("loaded vector index with %d vectors of dimension %d", index.ntotal, index.d)

    logger.info("loading index metadata from %s", index_file.with_suffix(".metadata"))
    index_metadata = {}
    n = index.ntotal
    with index_file.with_suffix(".metadata").open("rb") as f:
        data = f.read().decode("utf-8").split("\n")
        for d in data:
            (id, x, y, z) = tuple(map(int, d.split(" ")))
            index_metadata[id] = (x, y, z)

    logger.info("Loaded index metadata for %d vectors.", len(index_metadata))

    k = args.top_k
    result = collections.defaultdict(lambda: float("inf"))
    while len(result) < args.top_k and k < index.ntotal:
        distances, indices = index.search(np.array([v]), k)
        for i in range(k):
            idx = indices[0][i]
            dist = distances[0][i]
            if idx not in index_metadata:
                print("ERROR, no index ", idx, "of", len(index_metadata))
                continue
            tile = index_metadata[idx]
            if result[tile] > dist:
                result[tile] = dist
        k *= 2
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find tiles similar geometries.")
    parser.add_argument("index", type=str, help="Path to the FAISS indexes directory")
    parser.add_argument("geom", type=str, help="Geometry to find")
    parser.add_argument("--top_k", type=int, help="Number of top matches to return", default=10)
    args = parser.parse_args()

    s = shape(json.loads(args.geom))
    v = features.vectorizeGeom([o for o in s.geoms])

    results = {}
    for f in Path(args.index).iterdir():
        if not f.suffix.startswith(".faiss"):
            continue
        results |= find_in_file(f, v, args.top_k)

    wkts = []
    for i, (tile, dist) in enumerate(sorted(results.items(), key=lambda x: x[1])):
        wkts.append(geom.envelope_wkt(*tile))
        logger.info("Match %d: score: %f, tile: (%d, %d, %d)", i, dist, *tile)
    print(f"GEOMETRYCOLLECTION({', '.join(wkts)})")
