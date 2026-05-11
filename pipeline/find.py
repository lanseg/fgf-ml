import argparse
import faiss
import json
import logging

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
    args = parser.parse_args()

    logger.info("loading index from %s", args.index)
    index = faiss.read_index(args.index)
    index_metadata = []
    with open(f"{args.index}.metadata", "r") as f:
        index_metadata = json.load(f)
    logger.info("Loaded index with %d vectors of dimension %d", index.ntotal, index.d)

    s = shape(json.loads(args.geom))
    v = features.vectorize([o for o in s.geoms])

    k = 10
    distances, indices = index.search(np.array([v]), k)

    for i in range(k):
        idx = indices[0][i]
        meta = index_metadata[idx]
        logger.info(
            "Match %d: tile %d, score: %f, path: %s",
            i,
            idx,
            distances[0][i],
            geom.envelope_wkt(meta["x"], meta["y"], meta["z"]),
        )
