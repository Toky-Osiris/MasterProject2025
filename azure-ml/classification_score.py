########### CLASSIFICATION SCORE FUNCTIONS ###########
import os
import json
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image

def init():
    global model, device, class_names, input_size, hidden_size, num_classes, dropout_rate

    input_size = 3 * 780 * 780
    hidden_size = 500
    num_classes = 2
    class_names = [0, 1]  # 0: Do not spray, 1: Spray
    dropout_rate = 0.5
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    class NeuralNet(nn.Module):
        def __init__(self, input_size, hidden_size, num_classes, dropout_rate=0.5):
            super(NeuralNet, self).__init__()
            self.flatten = nn.Flatten()
            self.fc1 = nn.Linear(input_size, hidden_size)
            self.relu = nn.ReLU()
            self.dropout = nn.Dropout(dropout_rate)
            self.fc2 = nn.Linear(hidden_size, num_classes)

        def forward(self, x):
            x = self.flatten(x)
            out = self.fc1(x)
            out = self.relu(out)
            out = self.dropout(out)
            out = self.fc2(out)
            return out

    # Load model
    model_path = os.path.join(os.getenv("AZUREML_MODEL_DIR", "."), "classifier_model.pth")
    model = NeuralNet(input_size, hidden_size, num_classes, dropout_rate).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

def run(raw_data):
    try:
        # Expecting base64-encoded image or image bytes in JSON
        data = json.loads(raw_data)
        if "image" not in data:
            return {"error": "No image provided."}

        # Decode image
        from io import BytesIO
        import base64
        image_bytes = base64.b64decode(data["image"])
        image = Image.open(BytesIO(image_bytes)).convert('RGB')

        # Transform (must match training)
        transform = transforms.Compose([
            transforms.Resize((780, 780)),
            transforms.ToTensor()
        ])
        image_tensor = transform(image).unsqueeze(0).to(model.fc1.weight.device)

        # Predict
        with torch.no_grad():
            outputs = model(image_tensor)
            _, predicted = torch.max(outputs, 1)
            predicted_class = class_names[predicted.item()]
        return {"prediction": predicted_class}
    except Exception as e:
        return {"error": str(e)}
