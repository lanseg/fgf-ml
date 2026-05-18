import logging
from pathlib import Path

import numpy as np
import faiss

BATCH_SIZE = 10000

logger = logging.getLogger("main")


class Storage:
    def __init__(self, index_file: Path, vector_length: int):
        self.index_file = index_file
        self.index_metadata_file = self.index_file.with_suffix(".metadata")
        self.vector_length = vector_length
        self.vector_count = 0
        self.batch_count = 0
        self.index = None
        self.metadata = []

    def _get_batch_paths(self, batch: int):
        return (
            self.index_file.with_suffix(f".faiss_{batch}"),
            self.index_metadata_file.with_suffix(f".metadata_{batch}"),
        )

    def _save_batch(self):
        index_batch_path, metadata_batch_path = self._get_batch_paths(self.batch_count)
        logger.info(
            "saving batch %d, index of %d (%d) vectors to %s",
            self.batch_count,
            self.index.ntotal,
            len(self.metadata),
            index_batch_path,
        )
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

    def _init_index(self):
        if self.index is not None:
            self._save_batch()
            self.vector_count = 0
            self.batch_count += 1
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.vector_length))
        self.metadata = []

    def add(self, id: int, metadata, vector):
        if not self.index:
            self._init_index()
        self.index.add_with_ids(np.array([vector]), np.array([id]))
        self.metadata.append(f"{metadata[0]} {metadata[1]} {metadata[2]}")
        self.vector_count += 1
        if self.vector_count >= BATCH_SIZE:
            self._init_index()

    def _merge(self):
        logger.info(f"Merging {self.batch_count + 1} index batches...")
        final_index = None
        final_metadata = []
        for b in range(self.batch_count + 1):
            index_batch_path, metadata_batch_path = self._get_batch_paths(b)
            batch_index = faiss.read_index(str(index_batch_path))
            with metadata_batch_path.open("r") as f:
                final_metadata.extend(f.read().splitlines())
            if final_index is None:
                final_index = batch_index
            else:
                final_index.merge_from(batch_index, 0)
        logger.info(
            "saving index of %d (%d) vectors to %s",
            final_index.ntotal,
            len(final_metadata),
            self.index,
        )
        faiss.write_index(final_index, str(self.index_file))
        with self.index_metadata_file.open("w") as f:
            f.write("\n".join(final_metadata))
        logger.info(
            "saving index of %d (%d) vectors to %s",
            final_index.ntotal,
            len(final_metadata),
            self.index_file,
        )

    def _cleanup(self):
        logger.info("removing %s batch files...", self.batch_count)
        for b in range(self.batch_count + 1):
            index_batch_path, metadata_batch_path = self._get_batch_paths(b)
            index_batch_path.unlink()
            metadata_batch_path.unlink()
        logger.info("done removing %s batch files...", self.batch_count)

    def flush(self):
        self._save_batch()
        self._merge()
        self._cleanup()
