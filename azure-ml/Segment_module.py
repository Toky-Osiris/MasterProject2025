########### SEGMENTATION MODULE FUNCTIONS ###########
import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict
from skimage.transform import resize

class SegmentIt:
    def __init__(self, image_path, model_path="./best.pt"):
        self.image_path = image_path
        self.image = cv2.imread(image_path)
        self.image_rgb = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        self.model = YOLO(model_path)
        self.results = self.model(self.image_rgb)
        self.H, self.W, _ = self.image.shape
        self.cell_width = self.W / 3
        self.cell_height = self.H / 3
        self.reference_points = [
            (1507, 817), (980, 809), (442, 794),
            (1531, 271), (997, 286), (463, 235)
        ]
        self.class_names = {0: "plant", 1: "reference_panel"}
        self.masked_images_dict = defaultdict(list)

    def classify_masks(self):
        results = self.model(self.image)
        plant_masks = []
        reference_panel_masks = []
        target_classes = {"plant": plant_masks, "reference_panel": reference_panel_masks}
        for result in results:
            if result.masks is not None and result.boxes is not None:
                masks = result.masks.data.cpu().numpy()
                class_ids = result.boxes.cls.cpu().numpy()
                class_names = result.names
                for i, mask in enumerate(masks):
                    class_id = int(class_ids[i])
                    class_name = class_names[class_id]
                    if class_name in target_classes:
                        target_classes[class_name].append(mask)
        return target_classes

    def get_panel(self):
        masks = self.classify_masks()
        panel = masks["reference_panel"]
        reference_mask = np.array(panel[0]).astype(np.uint8)
        reference_mask = cv2.resize(reference_mask, (self.image.shape[1], self.image.shape[0]))
        reference_mask_3ch = np.expand_dims(reference_mask, axis=-1)
        reference_mask_3ch = np.repeat(reference_mask_3ch, 3, axis=-1)
        masked_image = self.image * reference_mask_3ch
        return masked_image

    def get_scaled_centroid(self, mask, orig_width, orig_height):
        y_indices, x_indices = np.where(mask == 1)
        centroid_x = np.mean(x_indices) * (orig_width / mask.shape[1])
        centroid_y = np.mean(y_indices) * (orig_height / mask.shape[0])
        return centroid_x, centroid_y

    def euclidean_distance(self, p1, p2):
        return np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

    def generate_masks(self):
        for result in self.results:
            if result.masks is not None and result.boxes is not None:
                masks = result.masks.data.cpu().numpy()
                class_ids = result.boxes.cls.cpu().numpy().astype(int)
                for i, mask in enumerate(masks):
                    class_id = class_ids[i]
                    class_name = self.class_names.get(class_id, f"Unknown {class_id}")
                    if class_name != "plant" or np.all(mask == 0):
                        continue
                    centroid_x, centroid_y = self.get_scaled_centroid(mask, self.W, self.H)
                    distances = [self.euclidean_distance((centroid_x, centroid_y), rp) for rp in self.reference_points]
                    closest_ref_point_idx = np.argmin(distances)
                    plant_label = f"plant {closest_ref_point_idx + 1}"
                    resized_mask = resize(mask, (self.H, self.W), mode='reflect', anti_aliasing=True)
                    resized_mask = (resized_mask > 0.5).astype(np.uint8)
                    masked_image = np.zeros_like(self.image)
                    masked_image[resized_mask == 1] = self.image[resized_mask == 1]
                    self.masked_images_dict[plant_label].append(masked_image)
            else:
                print("No masks found.")
        return self.masked_images_dict

def crop_and_pad(image):
    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    non_zero_indices = np.argwhere(image_gray != 0)
    y_min, x_min = non_zero_indices.min(axis=0)
    y_max, x_max = non_zero_indices.max(axis=0)
    img = image[y_min:y_max + 1, x_min:x_max + 1]
    current_shape = img.shape[:2]
    target_shape = (780, 780)
    pad_height = max(0, target_shape[0] - current_shape[0])
    pad_width = max(0, target_shape[1] - current_shape[1])
    top, bottom = pad_height // 2, pad_height - pad_height // 2
    left, right = pad_width // 2, pad_width - pad_width // 2
    padded_img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0])
    return padded_img

def mean_non_zero_with_threshold(array, channel, threshold):
    mask = channel <= threshold
    valid_pixels = array[(array != 0) & mask]
    return np.mean(valid_pixels) if len(valid_pixels) > 0 else 0

def correct_image(image, panel):
    image = crop_and_pad(image)
    rf = {"r": 0.178, "g": 0.175, "b": 0.166}
    b_panel = mean_non_zero_with_threshold(panel[:, :, 0], panel[:, :, 0], 223)
    g_panel = mean_non_zero_with_threshold(panel[:, :, 1], panel[:, :, 1], 211)
    r_panel = mean_non_zero_with_threshold(panel[:, :, 2], panel[:, :, 2], 206)
    b_plant = np.clip((image[:, :, 0] / b_panel) * rf["b"] * 255, 0, 255).astype(np.uint8)
    g_plant = np.clip((image[:, :, 1] / g_panel) * rf["g"] * 255, 0, 255).astype(np.uint8)
    r_plant = np.clip((image[:, :, 2] / r_panel) * rf["r"] * 255, 0, 255).astype(np.uint8)
    corrected_plant_image = cv2.merge([r_plant, g_plant, b_plant])
    return corrected_plant_image
