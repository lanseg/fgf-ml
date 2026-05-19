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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find tiles similar geometries.")
    parser.add_argument("index", type=str, help="Path to the FAISS index file")
    parser.add_argument("geom", type=str, help="Geometry to find")
    parser.add_argument("--top_k", type=int, help="Number of top matches to return", default=10)
    args = parser.parse_args()

    logger.info("loading vector index from %s", args.index)
    index = faiss.read_index(args.index)
    logger.info("Loaded vector index with %d vectors of dimension %d", index.ntotal, index.d)

    logger.info("loading index metadata from %s.metadata", args.index)
    index_metadata = []
    n = index.ntotal
    with Path(args.index).with_suffix(".metadata").open("rb") as f:
        data = f.read()
    index_metadata = data.decode("utf-8").split("\n")
    logger.info("Loaded index metadata for %d vectors.", len(index_metadata))

    s = shape(json.loads(args.geom))
    v = features.vectorizeGeom([o for o in s.geoms])

    k = args.top_k
    result = collections.defaultdict(lambda: float("inf"))

    while len(result) < args.top_k and k < index.ntotal:
        distances, indices = index.search(np.array([v]), k)
        for i in range(k):
            idx = indices[0][i]
            dist = distances[0][i]
            tile = tuple(map(int, index_metadata[idx].split(" ")))
            if result[tile] > dist:
                result[tile] = dist
        k *= 2
    wkts = []

    for i, (tile, dist) in enumerate(sorted(result.items(), key=lambda x: x[1])):
        wkts.append(geom.envelope_wkt(*tile))
        logger.info("Match %d: tile %d, score: %f, tile: (%d, %d, %d)", i, idx, dist, *tile)
    print(f"GEOMETRYCOLLECTION({', '.join(wkts)})")
