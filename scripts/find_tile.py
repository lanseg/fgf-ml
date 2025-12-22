import logging
import os
import torch
import faiss
import numpy as np
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

TILE_ROOT="data/tiles"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Load model and processor (same as extraction)
processor = AutoImageProcessor.from_pretrained("facebook/dinov2-base")
model = AutoModel.from_pretrained("facebook/dinov2-base").eval()  # Add .cuda() if GPU available

# Load FAISS index
index_path = "zurich_canton.index"
index = faiss.read_index(index_path)
logger.info("Loaded index with %d vectors", index.ntotal)

def listTiles(tileRoot):
    return sorted([
        os.path.join(tileRoot, zoom, tile)
        for zoom in os.listdir(tileRoot)
        for tile in os.listdir(os.path.join(tileRoot, zoom))
    ])

# Function to get embedding from an image file
def get_embedding(image_path):
    img = Image.open(image_path).convert("RGB")  # Assuming RGB; adjust if multi-channel
    inputs = processor(images=img, return_tensors="pt")  # .to("cuda") if GPU
    with torch.no_grad():
        outputs = model(**inputs)
        emb = outputs.last_hidden_state[:, 0].cpu().numpy()  # CLS token, shape (1, 768)
    return emb / np.linalg.norm(emb)  # Normalize if not already (for IP/cosine)

# Example: Query with user image
query_emb = get_embedding("search_sample.png")

# Search: Get top-k distances and indices
k = 10  # Top matches
distances, indices = index.search(query_emb, k)

allTiles = listTiles(TILE_ROOT)

# Print results (distances close to 1 are good matches for IP/cosine)
for i in range(k):
    if distances[0][i] > 0.5:  # Example threshold; tune based on your data
        logger.info("Match %d: Tile index %d, Score: %f, Path: %s",
        i, indices[0][i], distances[0][i], allTiles[indices[0][i]])
    else:
        break  # Stop at weak matches


# Now map indices back to tiles: You'll need your own metadata list
# e.g., tile_metadata = [{"zoom":16, "x":123, "y":456, "latlon": (47.3, 8.5)} ...]
# best_tile = tile_metadata[indices[0][0]]
