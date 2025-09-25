# AutomatedSprayer
AutomatedSprayer is an integrated system for automated plant (pea) spraying using computer vision and IoT. It leverages Azure ML for image segmentation/classification and Azure Functions for device control.

## Repository Structure

- **azure-functions/**: Azure Function App scripts for orchestrating the workflow and device control.
- **azure-ml/**: Scripts for Azure ML endpoints (segmentation and classification).
- **device/**: ESP32 controller and Raspberry Pi image capture/upload scripts.


## Setup & Deployment

### 1. Azure ML Endpoints
- Download the models from this link: 
- Register segmentation and classification models in Azure ML.
- Deploy endpoints using `segmentation_score.py` (with `segmentation_module.py`) and `classification_score.py`.
- Create an environment using `environment.yaml` for both endpoints(You can edit existing environments with the requirements in that file if errors appear)
 

### 2. Azure Functions
- Deploy `timer_trigger_function.py` to Azure Functions.
- Configure environment variables for endpoint URLs, API keys, and IoT Hub connection.

### 3. Device Integration
- Flash `arduino_controller.cpp` to ESP32.
- Run `collect_and_upload.py` on Raspberry Pi to capture and upload images to Azure Blob Storage.

## Usage

1. Raspberry Pi captures and uploads images daily (preferably during the day, use crontab for scheduling).
2. Azure Function triggers, downloads the image, calls segmentation and classification endpoints, and sends control signals to ESP32 via IoT Hub.
3. ESP32 activates solenoids and pump based on received signals.

## Requirements

- Azure ML workspace and endpoints
- Azure Functions App
- Azure Blob Storage
- Azure IoT Hub
- ESP32 and Raspberry Pi devices

## How to push your code to GitHub

1. **Initialize your repository (if not already done):**
    ```
    git init
    ```

2. **Add all files:**
    ```
    git add .
    ```

3. **Commit your changes:**
    ```
    git commit -m "Initial commit"
    ```

4. **Connect to your remote repository:**
    ```
    git remote add origin https://github.com/<your-username>/<your-repo-name>.git
    ```

5. **Push your code:**
    ```
    git push -u origin main
    ```
    *(If your branch is called `master`, use `master` instead of `main`)*

## License
MIT License
