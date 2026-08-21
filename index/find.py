import argparse
import collections
import json
import logging
import pathlib

import faiss
import numpy as np
from shapely.geometry import shape

import clip
import geom
import storage
import transform

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("find")

img_size = 224


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find tiles similar geometries.")
    parser.add_argument("index", type=str, help="Path to the FAISS indexes directory")
    parser.add_argument("geom", type=str, help="Geometry to find")
    parser.add_argument("--top_k", type=int, help="Number of top matches to return", default=10)
    args = parser.parse_args()

    s = transform.fit(shape(json.loads(args.geom)), (0, 0, img_size, img_size), keep_aspect=True)
    generator = clip.CLIPEmbeddingGenerator()

    img = clip.rasterize_geometry(s.geoms, img_size)
    emb = generator.generate_batch_embeddings([img])[0]

    index = storage.Storage(pathlib.Path(args.index), 512)
    results = index.find(emb, args.top_k)

    wkts = []
    for i, (tile, dist) in enumerate(sorted(results.items(), key=lambda x: x[1])):
        awkt = geom.envelope_wkt(*tile)
        wkts.append(awkt)
        logger.info("Match %d: score: %f, tile: (%d, %d, %d) -> %s", i, dist, tile[0], tile[1], tile[2], awkt)
    print(f"GEOMETRYCOLLECTION({', '.join(wkts)})")
