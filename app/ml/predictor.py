import torch
import numpy as np
from PIL import Image
from torchvision import transforms
from .model import model
from .labels import DISEASE_LABELS

# Image preprocessing pipeline
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.Grayscale(num_output_channels=3),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

def predict_xray(image_path: str, top_k: int = 3):
    image = Image.open(image_path).convert("RGB")
    image = transform(image).unsqueeze(0)  # shape: [1, 3, 224, 224]

    with torch.no_grad():
        outputs = model(image)[0].numpy()

    predictions = []
    for idx, prob in enumerate(outputs):
        predictions.append({
            "disease": DISEASE_LABELS[idx],
            "confidence": round(float(prob), 3)
        })

    # Sort by confidence
    predictions.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "all_predictions": predictions,
        "top_3": predictions[:top_k]
    }
