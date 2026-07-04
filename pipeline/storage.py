import logging
from pathlib import Path

import faiss
import numpy as np

import features

BATCH_SIZE = 100000

logger = logging.getLogger("storage")


class Storage:
    def __init__(self, index_file: Path, vector_length: int, batch_size=BATCH_SIZE):
        self.index_file = index_file
        self.vector_length = vector_length
        self.vector_count = 0
        self.batch_count = 0
        self.batch_size = batch_size
        self.index = None
        self.metadata = []

    def _get_batch_paths(self, batch: int):
        stem = self.index_file.stem
        return (
            self.index_file.with_stem(f"{stem}_{batch}"),
            self.index_file.with_stem(f"{stem}_{batch}").with_suffix(".metadata"),
        )

    def _save_batch(self):
        assert self.index is not None

        index_batch_path, metadata_batch_path = self._get_batch_paths(self.batch_count)
        logger.info(
            "saving batch %d, index of %d (%d) vectors to %s",
            self.batch_count,
            self.index.ntotal,
            len(self.metadata),
            index_batch_path,
        )
        metadata_batch_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(index_batch_path))
        with metadata_batch_path.open("w") as f:
            f.write("\n".join(self.metadata))
        logger.info(
            "done saving batch %d, index of %d (%d) vectors to %s",
            self.batch_count,
            self.index.ntotal,
            len(self.metadata),
            index_batch_path,
        )
        self.batch_count += 1

    def _init_index(self):
        if self.index is not None:
            self._save_batch()
            self.vector_count = 0
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.vector_length))
        self.metadata = []

    def add(self, id: int, fv: features.FeatureVector):
        if not self.index:
            self._init_index()
        self.index.add_with_ids(np.array([fv.vector]), np.array([id]))
        self.metadata.append(f"{id} {fv.tile[0]} {fv.tile[1]} {fv.tile[2]}")
        self.vector_count += 1
        if self.vector_count >= self.batch_size:
            self._init_index()

    def flush(self):
        logger.info("saving the last batch")
        self._save_batch()
