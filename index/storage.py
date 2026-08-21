import collections
import dbm
import logging
from dataclasses import dataclass
from pathlib import Path

import faiss
import numpy as np

import tilesource

BATCH_SIZE = 100000

logger = logging.getLogger("storage")


@dataclass
class TileEmbedding:
    tile: tuple[int, int, int]
    vector: np.ndarray


class Shard:
    def __init__(self, index_file: Path, metadata_file: Path, vector_length: int):
        self.index_file = index_file
        self.metadata_file = metadata_file
        self.vector_length = vector_length
        self.open = False
        self.index = None
        self.metadata = None

    def _open(self):
        if not self.index_file.exists():
            self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.vector_length))
            self.metadata = dbm.open(self.metadata_file, "c")
            self.open = True
            return
        logger.info("loading vector index from %s", self.index_file)
        self.index = faiss.read_index(str(self.index_file))
        logger.info(
            "loaded vector index with %d vectors of dimension %d", self.index.ntotal, self.index.d
        )

        logger.info("loading index metadata from %s", self.metadata_file)
        self.metadata = dbm.open(self.metadata_file, "c")
        logger.info("Loaded index metadata for %d vectors.", len(self.metadata))
        self.open = True

    def add(self, id: int, fv: TileEmbedding):
        if not self.open:
            self._open()
        self.index.add_with_ids(np.array([fv.vector]), np.array([id]))
        self.metadata[str(id)] = f"{fv.tile[0]},{fv.tile[1]},{fv.tile[2]}"

    def find(self, emb: np.array, top_k: int):
        if not self.open:
            self._open()
        result = collections.defaultdict(lambda: float("inf"))
        k = top_k
        while len(result) < top_k and k <= self.index.ntotal:
            distances, indices = self.index.search(emb, k)
            for i in range(k):
                idx = str(indices[0][i]).encode("utf-8")
                dist = distances[0][i]

                if idx not in self.metadata:
                    logger.warn("no metadata for %d", idx)
                    continue
                tile = tuple(map(int, self.metadata[idx].decode("utf-8").split(",")))
                if result[tile] > dist:
                    result[tile] = dist
            k *= 2
        return result

    def close(self):
        if not self.open:
            return
        faiss.write_index(self.index, str(self.index_file))
        self.metadata.close()


class Storage:
    def __init__(self, index_root: Path, vector_length: int, batch_size=BATCH_SIZE):
        self.index_root = index_root
        self.vector_length = vector_length
        self.vector_count = 0
        self.batch_count = 0
        self.batch_size = batch_size
        self.shard = None

        if not self.index_root.exists():
            self.index_root.mkdir(parents=True)

    def _get_batch_paths(self, batch: int):
        return (
            self.index_root / f"{batch}_{self.batch_count}.faiss",
            self.index_root / f"{batch}_{self.batch_count}.metadata",
        )

    def _save_batch(self):
        assert self.shard is not None
        logger.info(
            "saving batch %d, index of %d vectors to %s",
            self.batch_count,
            self.shard.index.ntotal,
            self.shard.index_file,
        )
        self.shard.close()
        logger.info(
            "done saving batch %d, index of %d vectors to %s",
            self.batch_count,
            self.shard.index.ntotal,
            self.shard.index_file,
        )
        self.batch_count += 1

    def _init_index(self):
        if self.shard is not None:
            self.shard.close()
        self.shard = Shard(
            *self._get_batch_paths(self.batch_count), vector_length=self.vector_length
        )
        logger.info("created a new shard at %s", self.shard.index_file)

    def add(self, id: int, fv: TileEmbedding):
        if not self.shard:
            self._init_index()
        self.shard.add(id, fv)

        self.vector_count += 1
        if self.vector_count >= self.batch_size:
            self.vector_count = 0
            self.batch_count += 1
            self._init_index()

    def find(self, emb: np.array, top_k: int) -> list[tilesource.Tile]:
        result = {}
        _vector = np.array([emb])
        for f in Path(self.index_root).iterdir():
            if not f.suffix.startswith(".faiss"):
                continue
            s = Shard(f, f.with_suffix(".metadata"), self.vector_length)
            shard_result = s.find(_vector, top_k)
            for k, v in shard_result.items():
                if k not in result or result[k] < v:
                    result[k] = v
            logger.info("searched %s, found %d (%d total)", f.name, len(shard_result), len(result))
        return dict(list(sorted(result.items(), key=lambda x: x[1]))[:top_k])

    def flush(self):
        logger.info("saving the last batch")
        self._save_batch()
