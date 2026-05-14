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

    logger.info("loading vector index from %s", args.index)
    index = faiss.read_index(args.index)
    logger.info("Loaded vector index with %d vectors of dimension %d", index.ntotal, index.d)

    logger.info("loading index metadata from %s.metadata", args.index)
    index_metadata = []
    n = index.ntotal
    with open(f"{args.index}.metadata", "rb") as f:
        data = f.read()
    index_metadata = data.decode("utf-8").split("\n")
    logger.info("Loaded index metadata for %d vectors.", len(index_metadata))

    s = shape(json.loads(args.geom))
    v = features.vectorizeGeom([o for o in s.geoms])

    k = 10
    distances, indices = index.search(np.array([v]), k)

    wkts = []
    for i in range(k):
        idx = indices[0][i]
        meta_str = index_metadata[idx]
        meta = tuple(map(int, meta_str.split(" ")))
        wkts.append(geom.envelope_wkt(meta[0], meta[1], meta[2]))
        logger.info(
            "Match %d: tile %d, score: %f, tile: (%d, %d, %d)",
            i,
            idx,
            distances[0][i],
            *meta
        )
    print(f"GEOMETRYCOLLECTION({", ".join(wkts)})")