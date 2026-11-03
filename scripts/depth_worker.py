"""Offline CPU worker, isolated from Gradio's dependencies."""
from pathlib import Path
import sys
import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

model_dir = Path(__file__).resolve().parents[1] / "models" / "depth-anything-v2-small"
torch.set_num_threads(max(1, min(8, torch.get_num_threads())))
processor = AutoImageProcessor.from_pretrained(model_dir, local_files_only=True)
model = AutoModelForDepthEstimation.from_pretrained(model_dir, local_files_only=True).eval()
with Image.open(sys.argv[1]) as image:
    inputs = processor(images=image.convert("RGB"), return_tensors="pt")
with torch.inference_mode():
    depth = model(**inputs).predicted_depth[0].cpu().numpy()
np.save(sys.argv[2], depth)
