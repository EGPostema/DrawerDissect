import os
from functions.resize_drawer import resize_drawer_images
from functions.infer_drawers import infer_drawers
from functions.crop_trays import crop_trays_from_fullsize
from functions.resize_trays import resize_tray_images
from functions.label_transcription import transcribe_labels_and_ids
from functions.infer_trays import infer_tray_images
from functions.crop_specimens import crop_specimens_from_trays

# Set base directory
base_dir = os.path.abspath(os.path.dirname(__file__))

# User inputs for API key and model details **MAKE SURE TO MODIFY THIS**
API_KEY = 'YOUR_API_KEY'

# User inputs for roboflow model that seperates TRAYS from DRAWERS **MAKE SURE TO MODIFY THIS**
DRAWER_MODEL_ENDPOINT = 'YOUR_DRAWER_MODEL_ENDPOINT'
DRAWER_MODEL_VERSION = 1  # Adjust the version as needed

# User inputs for roboflow model that seperates SPECIMENS from TRAYS **MAKE SURE TO MODIFY THIS**
TRAY_MODEL_ENDPOINT = 'YOUR_TRAY_MODEL_ENDPOINT'
TRAY_MODEL_VERSION = 1  # Adjust the version as needed

# Define directories
fullsize_dir = 'coloroptera/drawers/fullsize'
resized_dir = 'coloroptera/drawers/resized'
coordinates_dir = os.path.join(resized_dir, 'coordinates')
trays_dir = 'coloroptera/drawers/trays'
resized_trays_dir = 'coloroptera/drawers/resized_trays'
resized_trays_coordinates_dir = os.path.join(resized_trays_dir, 'coordinates')
specimens_dir = 'coloroptera/drawers/specimens'

# Ensure necessary directories exist
os.makedirs(resized_dir, exist_ok=True)
os.makedirs(coordinates_dir, exist_ok=True)
os.makedirs(trays_dir, exist_ok=True)
os.makedirs(resized_trays_dir, exist_ok=True)
os.makedirs(resized_trays_coordinates_dir, exist_ok=True)
os.makedirs(specimens_dir, exist_ok=True)

def main():
    print("Starting the image processing pipeline...")
    
    # Step 1: Shrink Fullsize Drawer Images
    resize_drawer_images(fullsize_dir, resized_dir)
    print(f"Resized images saved in {resized_dir}")

    # Step 2: Run Inference on Resized Drawers to Detect Trays
    infer_drawers(resized_dir, coordinates_dir, API_KEY, DRAWER_MODEL_ENDPOINT, DRAWER_MODEL_VERSION)
    print(f"Inference results saved in {coordinates_dir}")

    # Step 3: Crop Trays from Fullsize Drawer Images
    crop_trays_from_fullsize(fullsize_dir, resized_dir, trays_dir)
    print(f"Cropped tray images saved in {trays_dir}")

    # Step 4: Shrink Trays Images
    resize_tray_images(trays_dir, resized_trays_dir)
    print(f"Resized tray images saved in {resized_trays_dir}")

    # Step 5: Transcribe Labels from Resized Trays into CSV File
    transcribe_labels_and_ids(resized_trays_dir)
    print(f"Labels transcribed and saved in {os.path.join(resized_trays_dir, 'label_data')}")

    # Step 6: Run Inference on Resized Trays to Detect Individual Specimens
    infer_tray_images(resized_trays_dir, resized_trays_coordinates_dir, API_KEY, TRAY_MODEL_ENDPOINT, TRAY_MODEL_VERSION)
    print(f"Inference results for trays saved in {resized_trays_coordinates_dir}")

    # Step 7: Crop Specimens from Trays
    crop_specimens_from_trays(trays_dir, resized_trays_dir, specimens_dir)
    print(f"Cropped specimen images saved in {specimens_dir}")

    print("Image processing pipeline completed.")

if __name__ == '__main__':
    main()

