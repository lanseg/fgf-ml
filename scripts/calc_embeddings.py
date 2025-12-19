import os
import json
import logging
import sys
import torch
from multiprocessing import cpu_count
from torchvision.transforms import Compose, Resize, Normalize
from transformers import AutoImageProcessor, AutoModel
from torch.utils.data import DataLoader, Subset, Dataset
from PIL import Image
import faiss
import numpy as np

TILE_PATH = os.environ.get("TILE_PATH", "data/tiles")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "128"))
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "1000"))
NUM_WORKERS = int(os.environ.get("NUM_WORKERS", str(cpu_count())))
INDEX_PATH = os.environ.get("INDEX_PATH", "zurich_canton.index")
CHECKPOINT_PATH = os.environ.get("CHECKPOINT_PATH", "checkpoint.json")

dataloader_params = {
    'batch_size': BATCH_SIZE,
    'num_workers': NUM_WORKERS - 1,
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class TileDataset(Dataset):
    def __init__(self, tile_paths):
        self.tile_paths = tile_paths  # List of str paths, e.g., ['data/tiles/16/34299_22943.png', ...]

    def __len__(self):
        return len(self.tile_paths)

    def __getitem__(self, idx):
        path = self.tile_paths[idx]
        try:
            img = Image.open(path).convert("RGB")  # Load as PIL.Image; adjust mode if multi-channel
            img.load()
            return img
        except Exception as e:
            logger.warning("Failed to load image #%d (%s): %s", idx, path, e)
            return None

def collateSkipEmpty(items):
    return list(filter(lambda x: x, items))

def loadIndex(index_path, checkpoint_path):
    index = None
    checkpoint = None
    try:
        index = faiss.read_index(index_path)
        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)
    except Exception:
        dim = 768  # DinoV2-base
        index = faiss.IndexFlatIP(dim)  # Or your preferred index type
        checkpoint = {'last_processed': -1}
    return (index, checkpoint)

def loadDataset(tileRoot):
    dataset =  sorted([
        os.path.join(tileRoot, zoom, tile)
        for zoom in os.listdir(tileRoot)
        for tile in os.listdir(os.path.join(tileRoot, zoom))
    ])
    logger.info("Found %d tiles at %s", len(dataset), tileRoot)
    return TileDataset(dataset)

if __name__ == '__main__':
    deviceType = "gpu" if torch.cuda.is_available() else "cpu"
    device = torch.device(deviceType)
    logger.info("Using device: %s", deviceType)
    if deviceType == "gpu":
        for i in range(torch.cuda.device_count()):
            logger.info("\tGPU device [%d]: %s", i, torch.cuda.get_device_name(i))

    logger.info("Loading model and processor...")
    processor = AutoImageProcessor.from_pretrained("facebook/dinov2-base")
    model = AutoModel.from_pretrained("facebook/dinov2-base").to(device).eval()
    logger.info("Device: %s", deviceType)


    dataset = loadDataset(TILE_PATH)
    index, checkpoint = loadIndex(INDEX_PATH, CHECKPOINT_PATH)
    start_idx = checkpoint['last_processed'] + 1
    logger.info("Starting from tile %d", start_idx)

    total_tiles = len(dataset)
    # Process in chunks
    for chunk_start in range(start_idx, total_tiles, CHUNK_SIZE):
        chunk_end = min(chunk_start + CHUNK_SIZE, total_tiles)
        logger.info("Processing tiles %d to %d", chunk_start, chunk_end - 1)

        # Subset for this chunk
        chunk_dataset = Subset(dataset, range(chunk_start, chunk_end))
        dataloader = DataLoader(chunk_dataset,  collate_fn=collateSkipEmpty, **dataloader_params)

        embeddings = []
        for batch in dataloader:
            inputs = processor(images=batch, return_tensors="pt")
            with torch.no_grad():
                batch_emb = model(**inputs).last_hidden_state[:, 0].cpu().numpy()
            embeddings.extend(batch_emb)

        # Normalize and add to index
        embeddings = np.array(embeddings)
        faiss.normalize_L2(embeddings)  # If using cosine/IP
        index.add(embeddings)

        # Save checkpoint and index
        checkpoint['last_processed'] = chunk_end - 1
        with open(CHECKPOINT_PATH, 'w') as f:
            json.dump(checkpoint, f)
        faiss.write_index(index, INDEX_PATH)
        logger.info("Checkpoint saved at %d", chunk_end)

    logger.info("Done.")