#### This is the code for the control module (Azure Function Apps) ##########
import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.iot.hub import IoTHubRegistryManager
from io import BytesIO
from PIL import Image
import datetime
import requests
import json
import base64

app = func.FunctionApp()

BLOB_CONNECTION_STRING = <blob connection string>
CONTAINER_NAME = <container>
SEGMENT_ENDPOINT = <segmenter’s endpoint>
SEGMENT_API_KEY = <segmenter’s API key>
CLASSIFY_ENDPOINT = <classifier’s endpoint>
CLASSIFY_API_KEY = <classifier’s API key>
IOTHUB_CONNECTION_STRING = <IoThub connection string>
DEVICE_ID = <Device id>

# =================== MAIN ENTRY ===================
@app.schedule(schedule="* 30 20 * * *", arg_name="myTimer", run_on_startup=True, use_monitor=False)  # run at 8:30 PM daily
def timer_trigger(myTimer: func.TimerRequest) -> None:
    utc_now = datetime.datetime.utcnow()
    logging.info(f"Timer trigger function started at {utc_now.isoformat()}")
    try:
        # Download image
        blob_bytes = get_image()
        logging.info("Image downloaded from Blob Storage.")

        # Segment image
        segment_results = segment(blob_bytes)
        if not segment_results:
            logging.error("Segmentation failed or returned empty.")
            return

        corrected_images = segment_results.get("corrected_images", {})
        logging.info(f"Segmented images: {list(corrected_images.keys())}")

        # Build signal
        signal = [0] * 6
        plants = ["plant 1", "plant 2", "plant 3", "plant 4", "plant 5", "plant 6"]
        for i, plant in enumerate(plants):
            logging.info(f"Analyzing {plant}...")
            if plant in corrected_images:
                try:
                    image_bytes = base64.b64decode(corrected_images[plant][0])
                    prediction = classify(image_bytes)
                    signal[i] = prediction
                    logging.info(f"Classification result for {plant}: {prediction}")
                except Exception as e:
                    logging.error(f"Error classifying {plant}: {e}")
            else:
                logging.warning(f"{plant} not found in segmentation output.")

        # Send signal
        send_signal(signal)
        logging.info(f"Signal sent: {signal}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

# =================== HELPERS ===================
def get_image():
    """Downloads today's image from Azure Blob Storage and returns it as bytes."""
    blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)
    now = datetime.datetime.now()
    blob_name = f"pea_{now.year}-{now.month}-{now.day}.png"
    blob_client = container_client.get_blob_client(blob_name)
    stream_downloader = blob_client.download_blob()
    blob_bytes = stream_downloader.readall()
    return blob_bytes

def segment(image_bytes):
    """Consumes YOLO segmentation model in Azure ML."""
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    payload = {"image": encoded_image}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SEGMENT_API_KEY}"
    }
    response = requests.post(SEGMENT_ENDPOINT, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Segmentation request failed: {response.status_code} {response.text}")
        return {}

def classify(image_bytes):
    """Invokes the classification model in Azure ML."""
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    payload = {"image": encoded_image}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CLASSIFY_API_KEY}"
    }
    response = requests.post(CLASSIFY_ENDPOINT, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json().get("prediction", 0)
    else:
        logging.error(f"Classification request failed: {response.status_code} {response.text}")
        return 0

def send_signal(signal):
    """Sends the final signal list to the ESP32 via IoT Hub."""
    registry_manager = IoTHubRegistryManager(IOTHUB_CONNECTION_STRING)
    payload = json.dumps({"signal": signal})
    registry_manager.send_c2d_message(DEVICE_ID, payload)
