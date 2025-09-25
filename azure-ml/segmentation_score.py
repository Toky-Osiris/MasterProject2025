########### SEGMENTATION SCORE FUNCTIONS ###########
import json
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import os
from segment_module import SegmentIt, correct_image

def decode_base64_image(base64_str):
    image_data = base64.b64decode(base64_str)
    image_np = np.array(Image.open(BytesIO(image_data)).convert("RGB"))  # Ensures compatibility with PNG, etc.
    return cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

def encode_image_to_base64(image):
    _, buffer = cv2.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")

def init():
    global yolo_model_path
    yolo_model_path = os.path.join(os.getenv("AZUREML_MODEL_DIR", "."), "best.pt")

def run(raw_data):
    try:
        inputs = json.loads(raw_data)
        img = decode_base64_image(inputs["image"])
        # Save image temporarily for SegmentIt
        temp_path = "temp_input.jpg"
        cv2.imwrite(temp_path, img)
        segmenter = SegmentIt(temp_path, model_path=yolo_model_path)
        panel = segmenter.get_panel()
        masks = segmenter.generate_masks()
        result = {}
        for label, imgs in masks.items():
            corrected_list = []
            for plant_img in imgs:
                corrected = correct_image(plant_img, panel)
                corrected_list.append(encode_image_to_base64(corrected))
            result[label] = corrected_list
        return {"corrected_images": result}
    except Exception as e:
        return {"error": str(e)}
