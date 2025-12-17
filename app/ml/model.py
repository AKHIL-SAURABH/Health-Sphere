import torch
import torchvision.models as models

def load_model():
    model = models.densenet121(pretrained=True)

    # Modify classifier for multi-label output (14 diseases)
    num_features = model.classifier.in_features
    model.classifier = torch.nn.Sequential(
        torch.nn.Linear(num_features, 14),
        torch.nn.Sigmoid()  # multi-label probabilities
    )

    model.eval()  # inference mode
    return model

model = load_model()
