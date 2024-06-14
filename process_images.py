# Import os, argparse, and roboflow to make directories & define roboflow details

import os
import argparse
import roboflow

# Set base directory
base_dir = os.path.abspath(os.path.dirname(__file__))

# User inputs for API key and model details **MAKE SURE TO MODIFY THIS!**
API_KEY = 'YOUR_API_HERE'
WORKSPACE = 'YOUR_WORKSPACE_HERE'

# Initialize Roboflow
rf = roboflow.Roboflow(api_key=API_KEY)
workspace = rf.workspace(WORKSPACE)

# User inputs for roboflow model that seperates TRAYS from DRAWERS **MAKE SURE TO MODIFY THIS!**
DRAWER_MODEL_ENDPOINT = 'TRAY_SEPERATING_MODEL_HERE'
DRAWER_MODEL_VERSION = 1  # Adjust the version as needed!

# User inputs for roboflow model that seperates SPECIMENS from TRAYS **MAKE SURE TO MODIFY THIS!**
TRAY_MODEL_ENDPOINT = 'SPECIMEN_SEPERATING_MODEL_HERE'
TRAY_MODEL_VERSION = 1  # Adjust the version as needed

# Define directories
fullsize_dir = 'drawers/fullsize'
resized_dir = 'drawers/resized'
coordinates_dir = os.path.join(resized_dir, 'coordinates')
trays_dir = 'drawers/trays'
resized_trays_dir = 'drawers/resized_trays'
resized_trays_coordinates_dir = os.path.join(resized_trays_dir, 'coordinates')
specimens_dir = 'drawers/specimens'

# Ensure necessary directories exist
directories = [fullsize_dir, resized_dir, coordinates_dir, trays_dir, resized_trays_dir, resized_trays_coordinates_dir, specimens_dir]
all_exist = True
for directory in directories:
    if not os.path.exists(directory):
        print(f"Creating directory: {directory}")
        os.makedirs(directory, exist_ok=True)
        all_exist = False

if all_exist:
    print("All directories exist.")

# Import functions from functions folder

from functions.resize_drawer import resize_drawer_images
from functions.infer_drawers import infer_drawers
from functions.crop_trays import crop_trays_from_fullsize
from functions.resize_trays import resize_tray_images
from functions.label_transcription import transcribe_labels_and_ids
from functions.infer_trays import infer_tray_images
from functions.crop_specimens import crop_specimens_from_trays

def main():
    
    # You can adjust the preferred % confidence and object overlap for each model (drawers to trays & trays to specimens) here. 
    # The default is 50% for both; e.g., the model only reports predictions where it is more than 50% confident, and expects object bounding boxes to overlap.    
    
    parser = argparse.ArgumentParser(description="Process images with specified confidence and overlap.")
    parser.add_argument('step', choices=['resize_drawers', 'infer_drawers', 'crop_trays', 'resize_trays', 'transcribe_labels', 'infer_trays', 'crop_specimens'],
                        help="Step to execute")
    parser.add_argument('--drawer_confidence', type=int, default=50, help="Confidence level for drawer inference. Default is 50.")
    parser.add_argument('--drawer_overlap', type=int, default=50, help="Overlap level for drawer inference. Default is 50.")
    parser.add_argument('--tray_confidence', type=int, default=50, help="Confidence level for tray inference. Default is 50.")
    parser.add_argument('--tray_overlap', type=int, default=50, help="Overlap level for tray inference. Default is 50.")
    
    args = parser.parse_args()

    # Let's process some images!
    print("Starting the image processing pipeline...")

    # Step 1: Shrink Fullsize Drawer Images
    if args.step == 'resize_drawers':
        resize_drawer_images(fullsize_dir, resized_dir)
        print(f"Resized drawers saved in {resized_dir}")
        
    # Step 2: Run Inference on Resized Drawers to Detect Trays
    elif args.step == 'infer_drawers':
        infer_drawers(resized_dir, coordinates_dir, API_KEY, DRAWER_MODEL_ENDPOINT, DRAWER_MODEL_VERSION, confidence=args.drawer_confidence, overlap=args.drawer_overlap)
        print(f"Tray bounding boxes saved in {coordinates_dir}")
        
    # Step 3: Crop Trays from Fullsize Drawer Images
    elif args.step == 'crop_trays':
        crop_trays_from_fullsize(fullsize_dir, resized_dir, trays_dir)
        print(f"Cropped trays saved in {trays_dir}")

    # Step 4: Shrink Tray Images
    elif args.step == 'resize_trays':
        resize_tray_images(trays_dir, resized_trays_dir)
        print(f"Resized tray images saved in {resized_trays_dir}")

    # Step 5: Transcribe Labels from Resized Trays into CSV File
    elif args.step == 'transcribe_labels':
        transcribe_labels_and_ids(resized_trays_dir)
        print(f"Labels transcribed and saved in {os.path.join(resized_trays_dir, 'label_data')}")

    # Step 6: Run Inference on Resized Trays to Detect Individual Specimens
    elif args.step == 'infer_trays':
        infer_tray_images(resized_trays_dir, resized_trays_coordinates_dir, API_KEY, TRAY_MODEL_ENDPOINT, TRAY_MODEL_VERSION, confidence=args.tray_confidence, overlap=args.tray_overlap)
        print(f"Specimen bounding boxes for all trays saved in {resized_trays_coordinates_dir}")
        
    # Step 7: Crop Specimens from Trays
    elif args.step == 'crop_specimens':
        crop_specimens_from_trays(trays_dir, resized_trays_dir, specimens_dir)
        print(f"Cropped specimens saved in {specimens_dir}")

    print("Image processing pipeline completed.")

if __name__ == '__main__':
    main()
