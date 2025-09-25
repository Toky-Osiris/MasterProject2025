################ This program collects images using a Raspberry Pi camera and uploads them to Azure Blob Storage ################

from azure.storage.blob import BlobServiceClient
import csv
from datetime import datetime
import picamera
from picamera import PiCamera
from time import sleep

# capture_image
def collect_data():
    settings = {
        'awb_mode': 'auto',
        'exposure_compensation': -5,
        'iso': 100,
        'saturation': 0,
        'shutter_speed': 0
    }

    camera_RGB = PiCamera(camera_num=0)
    camera_RGB.start_preview()
    camera_RGB.resolution = (1920, 1080)
    camera_RGB.rotation = 180
    current_date = str(datetime.now())[0:10]

    # RGB
    try:
        # Apply the specified camera settings
        camera_RGB.awb_mode = settings['awb_mode']
        # camera_RGB.brightness = settings['brightness']
        camera_RGB.exposure_compensation = settings['exposure_compensation']
        camera_RGB.iso = settings['iso']
        camera_RGB.saturation = settings['saturation']
        camera_RGB.shutter_speed = settings['shutter_speed']
        # Optional: Allow the camera to adjust its settings
        sleep(2)
        # Capture an image with the given settings
        # naming format: treatmenttype_#tray_date
        output_file = f'/home/pi/Documents/vertical farming/pea_image/pea_{current_date}.png'
        filename = f'pea_{current_date}.png'
        camera_RGB.capture(output_file)
        camera_RGB.stop_preview()
        print('Image captured')
        return output_file, filename
    except Exception as e:
        print(f'Error capturing image: {e}')

# Send the file to Azure
def send_file(IMAGE_PATH, BLOB_NAME):
    # declare the sas url of the container and the container_name
    SAS_URL = "ENTER_SAS_URL"
    CONTAINER_NAME = "data"  # the name of the container
    # Initialize the BlobServiceClient
    blob_service_client = BlobServiceClient(account_url=SAS_URL)  # Create the client and access the blob storage account itself
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=BLOB_NAME)

    with open(IMAGE_PATH, "rb") as image_file:
        print("Uploading image to Azure Blob Storage...")
        blob_client.upload_blob(image_file, overwrite=True)
        print("Image uploaded successfully!")

if __name__ == "__main__":
    IMAGE_PATH, BLOB_NAME = collect_data()
    send_file(IMAGE_PATH, BLOB_NAME)
