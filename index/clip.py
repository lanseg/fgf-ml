import logging

import cv2
import numpy as np
import shapely
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import models, transforms
from transformers import CLIPModel, CLIPProcessor

logger = logging.getLogger("clip")


def rasterize_geometry(geoms, img_size=224):
    """Renders polygons on a PIL canvas."""
    canvas = np.zeros((img_size, img_size), dtype=np.uint8)

    for poly in geoms:
        points = shapely.get_coordinates(poly).astype(np.int32)
        cv2.fillPoly(canvas, [points], color=255)

    # Image.fromarray(canvas).convert("RGB").save("input.png")
    return Image.fromarray(canvas).convert("RGB")


class CLIPEmbeddingGenerator:
    """Generated with a help of some chat bot."""

    def __init__(self, model_name="convnext", device=None):
        if device is not None:
            self.device = device
        elif torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

        logger.info(f"Loading {model_name} model on {self.device}...")

        # 1. Load the pre-trained model and strip the final classification layer
        if model_name == "convnext":
            # ConvNeXt Small
            weights = models.ConvNeXt_Small_Weights.DEFAULT
            base_model = models.convnext_small(weights=weights)

            # ConvNeXt's classifier is a Sequential block.
            # The final layer (index 2) is the 1000-class Linear layer.
            # We replace it with Identity to output the raw 768-dim features.
            base_model.classifier[2] = nn.Identity()
            self.embedding_dim = 768

        elif model_name == "resnet50":
            weights = models.ResNet50_Weights.DEFAULT
            base_model = models.resnet50(weights=weights)

            # ResNet's final layer is named 'fc'. Replace it with Identity.
            base_model.fc = nn.Identity()
            self.embedding_dim = 2048

        else:
            raise ValueError("model_name must be 'convnext' or 'resnet50'")

        self.model = base_model.to(self.device)
        self.model.eval()

        # 2. Standard ImageNet Preprocessing Pipeline
        self.transform = transforms.Compose(
            [
                transforms.Resize((512, 512)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

    @torch.no_grad()
    def generate_batch_embeddings(self, images: list[Image.Image]) -> np.ndarray:
        """Generates embeddings for a batch of images to saturate the GPU."""
        tensor_list = []
        for img in images:
            if img.mode != "RGB":
                img = img.convert("RGB")
            tensor_list.append(self.transform(img))

        # Stack into [Batch, Channels, Height, Width]
        batch_tensor = torch.stack(tensor_list).to(self.device)
        # Use mixed precision for a massive speedup on RTX 4090/Ada cards
        with torch.autocast(
            device_type="cuda" if "cuda" in self.device else "cpu", dtype=torch.float16
        ):
            features = self.model(batch_tensor)

        normalized_embeddings = F.normalize(features, p=2, dim=1)
        return normalized_embeddings.cpu().numpy().astype(np.float32)
