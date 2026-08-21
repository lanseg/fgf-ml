import cv2
import numpy as np
import shapely
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

import transform

def rasterize_geometry(geoms, img_size=224):
    """Renders polygons on a PIL canvas."""
    canvas = np.zeros((img_size, img_size), dtype=np.uint8)

    for poly in geoms:
        points = shapely.get_coordinates(poly).astype(np.int32)
        cv2.fillPoly(canvas, [points], color=255)

    # Image.fromarray(canvas).convert("RGB").save("input.png")
    return Image.fromarray(canvas).convert("RGB")


class CLIPEmbeddingGenerator:
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        """Initializes the pre-trained CLIP model and processor from HuggingFace."""
        print(f"Loading CLIP model: {model_name}...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()  # Set to evaluation mode

    @torch.no_grad()
    def generate_batch_embeddings(self, images: list[Image.Image]) -> np.ndarray:
        """Generates embeddings for a batch of images simultaneously."""

        # Convert all images to RGB
        inputs = self.processor(images=images, return_tensors="pt").to(self.device)
        outputs = self.model.get_image_features(**inputs)

        if hasattr(outputs, "image_embeds"):
            features = outputs.image_embeds
        elif hasattr(outputs, "pooler_output"):
            features = outputs.pooler_output
        elif isinstance(outputs, torch.Tensor):
            features = outputs
        else:
            features = outputs[0]

        # Normalize the batch and return an (N, 512) 2D array where N is a batch size
        normalized_embeddings = F.normalize(features, p=2, dim=1)
        return normalized_embeddings.cpu().numpy().astype(np.float32)
