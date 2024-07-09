# Import os, argparse, and roboflow to make directories & define roboflow details

import os
import argparse
import roboflow

# Set base directory
base_dir = os.path.abspath(os.path.dirname(__file__))

# User inputs for API key and model details **MAKE SURE TO MODIFY THIS!**
API_KEY = 'API-KEY-HERE'
WORKSPACE = 'WORKSPACE-ID-HERE'

# Initialize Roboflow
rf = roboflow.Roboflow(api_key=API_KEY)
workspace = rf.workspace(WORKSPACE)

# User inputs for roboflow models **MAKE SURE TO MODIFY THESE!**
DRAWER_MODEL_ENDPOINT = 'TRAY-SEPERATING-MODEL-HERE'
DRAWER_MODEL_VERSION = 1  # Adjust the version as needed!
TRAY_MODEL_ENDPOINT = 'SPECIMEN-SEPERATING-MODEL-HERE'
TRAY_MODEL_VERSION = 1  # Adjust the version as needed
LABEL_MODEL_ENDPOINT = 'LABEL-TRANSCRIPTION-MODEL-HERE'
LABEL_MODEL_VERSION = 1  # Adjust the version as needed!
MASK_MODEL_ENDPOINT = 'beetlemasker'
MASK_MODEL_VERSION = 9  # Adjust the version as needed!

# Define directories
directories = {
    'fullsize': 'drawers/fullsize',
    'resized': 'drawers/resized',
    'coordinates': 'drawers/resized/coordinates',
    'trays': 'drawers/trays',
    'resized_trays': 'drawers/resized_trays',
    'resized_trays_coordinates': 'drawers/resized_trays/coordinates',
    'specimens': 'drawers/specimens'
}

# Ensure necessary directories exist
for name, directory in directories.items():
    if not os.path.exists(directory):
        print(f"Creating directory: {directory}")
        os.makedirs(directory, exist_ok=True)

# Import functions from functions folder
from functions.resize_drawer import resize_drawer_images
from functions.infer_drawers import infer_drawers
from functions.crop_trays import crop_trays_from_fullsize
from functions.resize_trays import resize_tray_images
from functions.label_transcription import transcribe_labels_and_ids
from functions.infer_trays import infer_tray_images
from functions.crop_specimens import crop_specimens_from_trays

# Define roboflow commands

def load_roboflow_workspace_and_project():
    rf = roboflow.Roboflow(api_key=API_KEY)
    workspace = rf.workspace(WORKSPACE)

# Use argparser to allow individual steps to be called (see README for commands)

def main():
    parser = argparse.ArgumentParser(description="Process images with specified confidence and overlap.")
    parser.add_argument('step', nargs='?', choices=['all', 'resize_drawers', 'infer_drawers', 'crop_trays', 'resize_trays', 'transcribe_labels', 'infer_trays', 'crop_specimens'],
                        default='all', help="Step to execute")
    parser.add_argument('--drawer_confidence', type=int, default=50, help="Confidence level for drawer inference. Default is 50.")
    parser.add_argument('--drawer_overlap', type=int, default=50, help="Overlap level for drawer inference. Default is 50.")
    parser.add_argument('--tray_confidence', type=int, default=50, help="Confidence level for tray inference. Default is 50.")
    parser.add_argument('--tray_overlap', type=int, default=50, help="Overlap level for tray inference. Default is 50.")
    parser.add_argument('--label_confidence', type=int, default=50, help="Confidence level for label inference. Default is 50.")
    parser.add_argument('--label_overlap', type=int, default=50, help="Overlap level for label inference. Default is 50.")
    
    args = parser.parse_args()

    # Function to run all steps sequentially
    def run_all_steps():
        resize_drawer_images(directories['fullsize'], directories['resized'])
        print(f"Resized drawers saved in {directories['resized']}")

        infer_drawers(directories['resized'], directories['coordinates'], API_KEY, DRAWER_MODEL_ENDPOINT, DRAWER_MODEL_VERSION, confidence=args.drawer_confidence, overlap=args.drawer_overlap)
        print(f"Tray bounding boxes saved in {directories['coordinates']}")

        crop_trays_from_fullsize(directories['fullsize'], directories['resized'], directories['trays'])
        print(f"Cropped trays saved in {directories['trays']}")

        resize_tray_images(directories['trays'], directories['resized_trays'])
        print(f"Resized tray images saved in {directories['resized_trays']}")

        transcribe_labels_and_ids(directories['resized_trays'], API_KEY, LABEL_MODEL_ENDPOINT, LABEL_MODEL_VERSION, confidence=args.label_confidence, overlap=args.label_overlap)
        print(f"Labels transcribed and saved in {os.path.join(directories['resized_trays'], 'label_data')}")

        infer_tray_images(directories['resized_trays'], directories['resized_trays_coordinates'], API_KEY, TRAY_MODEL_ENDPOINT, TRAY_MODEL_VERSION, confidence=args.tray_confidence, overlap=args.tray_overlap)
        print(f"Specimen bounding boxes for all trays saved in {directories['resized_trays_coordinates']}")

        crop_specimens_from_trays(directories['trays'], directories['resized_trays'], directories['specimens'])
        print(f"Cropped specimens saved in {directories['specimens']}")

    # Let's process some images!
    print("Starting the image processing pipeline...")

    load_roboflow_workspace_and_project()

    if args.step == 'all':
        run_all_steps()
    elif args.step == 'resize_drawers':
        resize_drawer_images(directories['fullsize'], directories['resized'])
        print(f"Resized drawers saved in {directories['resized']}")
    elif args.step == 'infer_drawers':
        infer_drawers(directories['resized'], directories['coordinates'], API_KEY, DRAWER_MODEL_ENDPOINT, DRAWER_MODEL_VERSION, confidence=args.drawer_confidence, overlap=args.drawer_overlap)
        print(f"Tray bounding boxes saved in {directories['coordinates']}")
    elif args.step == 'crop_trays':
        crop_trays_from_fullsize(directories['fullsize'], directories['resized'], directories['trays'])
        print(f"Cropped trays saved in {directories['trays']}")
    elif args.step == 'resize_trays':
        resize_tray_images(directories['trays'], directories['resized_trays'])
        print(f"Resized tray images saved in {directories['resized_trays']}")
    elif args.step == 'transcribe_labels':
        transcribe_labels_and_ids(directories['resized_trays'], API_KEY, LABEL_MODEL_ENDPOINT, LABEL_MODEL_VERSION, confidence=args.label_confidence, overlap=args.label_overlap)
        print(f"Labels transcribed and saved in {os.path.join(directories['resized_trays'], 'label_data')}")
    elif args.step == 'infer_trays':
        infer_tray_images(directories['resized_trays'], directories['resized_trays_coordinates'], API_KEY, TRAY_MODEL_ENDPOINT, TRAY_MODEL_VERSION, confidence=args.tray_confidence, overlap=args.tray_overlap)
        print(f"Specimen bounding boxes for all trays saved in {directories['resized_trays_coordinates']}")
    elif args.step == 'crop_specimens':
        crop_specimens_from_trays(directories['trays'], directories['resized_trays'], directories['specimens'])
        print(f"Cropped specimens saved in {directories['specimens']}")

    print("Image processing pipeline completed.")

if __name__ == '__main__':
    main()
