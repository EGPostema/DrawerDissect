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
MASK_MODEL_ENDPOINT = 'SPECIMEN-OUTLINING-MODEL-HERE'
MASK_MODEL_VERSION = 1  # Adjust the version as needed!
PATTERN_MODEL_ENDPOINT = 'PATTERN-CLASSIFYING-MODEL-HERE'
PATTERN_MODEL_VERSION = 1  # Adjust the version as needed!

# Define directories
directories = {
    'fullsize': 'drawers/fullsize',
    'resized': 'drawers/resized',
    'coordinates': 'drawers/resized/coordinates',
    'trays': 'drawers/trays',
    'resized_trays': 'drawers/resized_trays',
    'resized_trays_coordinates': 'drawers/resized_trays/coordinates',
    'label_coordinates': 'drawers/resized_trays/label_coordinates',
    'label_data': 'drawers/resized_trays/label_data',
    'specimens': 'drawers/specimens',
    'mask_coordinates': 'drawers/masks/mask_coordinates',
    'mask_csv': 'drawers/masks/mask_csv',
    'mask_png': 'drawers/masks/mask_png',
    'pattern_jsons': 'drawers/patterns/pattern_jsons',
    'pattern_data': 'drawers/patterns/pattern_data',
    'lengths': 'drawers/specimens/lengths',
    'merged_data': 'drawers/data'
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

# Ensure necessary directories exist
for name, directory in directories.items():
    if not os.path.exists(directory):
        print(f"Creating directory: {directory}")
        os.makedirs(directory, exist_ok=True)

# Define roboflow commands
def load_roboflow_workspace_and_project():
    rf = roboflow.Roboflow(api_key=API_KEY)
    workspace = rf.workspace(WORKSPACE)

# Helper function to run individual steps
def run_step(step, directories, args):
    print(f"Running step: {step}")

    if step == 'resize_drawers':
        resize_drawer_images(directories['fullsize'], directories['resized'])
        print(f"Resized drawers saved in {directories['resized']}")
    elif step == 'infer_drawers':
        infer_drawers(directories['resized'], directories['coordinates'], API_KEY, DRAWER_MODEL_ENDPOINT, DRAWER_MODEL_VERSION, confidence=args.drawer_confidence, overlap=args.drawer_overlap)
        print(f"Tray bounding boxes saved in {directories['coordinates']}")
    elif step == 'crop_trays':
        crop_trays_from_fullsize(directories['fullsize'], directories['resized'], directories['trays'])
        print(f"Cropped trays saved in {directories['trays']}")
    elif step == 'resize_trays':
        resize_tray_images(directories['trays'], directories['resized_trays'])
        print(f"Resized tray images saved in {directories['resized_trays']}")
    elif step == 'transcribe_labels_and_ids':
        transcribe_labels_and_ids(directories['resized_trays'], API_KEY, LABEL_MODEL_ENDPOINT, LABEL_MODEL_VERSION, confidence=args.label_confidence, overlap=args.label_overlap)
        print(f"Labels transcribed and saved in {os.path.join(directories['label_data'], 'labels.csv')}")
    elif step == 'infer_trays':
        infer_tray_images(directories['resized_trays'], directories['resized_trays_coordinates'], API_KEY, TRAY_MODEL_ENDPOINT, TRAY_MODEL_VERSION, confidence=args.tray_confidence, overlap=args.tray_overlap)
        print(f"Specimen bounding boxes for all trays saved in {directories['resized_trays_coordinates']}")
    elif step == 'crop_specimens':
        crop_specimens_from_trays(directories['trays'], directories['resized_trays'], directories['specimens'])
        print(f"Cropped specimens saved in {directories['specimens']}")
    elif step == 'infer_beetles':
        infer_beetles(directories['specimens'], directories['mask_coordinates'], API_KEY, MASK_MODEL_ENDPOINT, MASK_MODEL_VERSION, confidence=args.beetle_confidence, overlap=args.beetle_overlap)
        print(f"Segmentation mask coordinates saved in {directories['mask_coordinates']}")
    elif step == 'create_masks':
        create_masks(directories['mask_coordinates'], directories['mask_csv'], directories['mask_png'])
        print(f"Masked specimens .csv files saved in {directories['mask_csv']}")
        print(f"Masked specimens .png files saved in {directories['mask_png']}")
    elif step == 'infer_patterns':
        infer_patterns(directories['specimens'], directories['pattern_jsons'], API_KEY, PATTERN_MODEL_ENDPOINT, PATTERN_MODEL_VERSION)
        print(f"Pattern inferences saved in {directories['pattern_jsons']}")
    elif step == 'create_patterncsv':
        create_patterncsv(directories['pattern_jsons'], os.path.join(directories['pattern_data'], 'pattern_data.csv'))
        print(f"Pattern data csv saved in {directories['pattern_data']}")
    elif step == 'write_lengths':
        write_lengths(directories['mask_png'], os.path.join(directories['lengths'], 'lengths.csv'))
        print(f"Mask measurements saved in {os.path.join(directories['lengths'], 'lengths.csv')}")
    elif step == 'merge_datasets':
        merge_datasets(directories['label_data'] + '/labels.csv', 
                       directories['lengths'] + '/lengths.csv', 
                       directories['pattern_data'] + '/pattern_data.csv', 
                       directories['merged_data'] + '/coloroptera_data.csv')
        print(f"Merged datasets and saved in {directories['merged_data'] + '/coloroptera_data.csv'}")

    else:
        print(f"Unknown step: {step}")

# Use argparse to allow individual steps to be called (see README for commands)
def main():
    parser = argparse.ArgumentParser(description="Process images with specified confidence and overlap.")
    parser.add_argument('step', nargs='?', choices=['all', 'resize_drawers', 'infer_drawers', 'crop_trays', 'resize_trays', 'transcribe_labels_and_ids', 'infer_trays', 'crop_specimens', 'infer_beetles', 'create_masks', 'infer_patterns', 'create_patterncsv', 'write_lengths', 'merge_datasets'],
                        default='all', help="Step to execute")
    parser.add_argument('--drawer_confidence', type=int, default=50, help="Confidence level for drawer inference. Default is 50.")
    parser.add_argument('--drawer_overlap', type=int, default=50, help="Overlap level for drawer inference. Default is 50.")
    parser.add_argument('--tray_confidence', type=int, default=50, help="Confidence level for tray inference. Default is 50.")
    parser.add_argument('--tray_overlap', type=int, default=50, help="Overlap level for tray inference. Default is 50.")
    parser.add_argument('--label_confidence', type=int, default=50, help="Confidence level for label inference. Default is 50.")
    parser.add_argument('--label_overlap', type=int, default=50, help="Overlap level for label inference. Default is 50.")
    parser.add_argument('--beetle_confidence', type=int, default=50, help="Confidence level for specimen inference. Default is 50.")
    parser.add_argument('--beetle_overlap', type=int, default=50, help="Overlap level for specimen inference. Default is 50.")
    
    args = parser.parse_args()

    # Let's process some images!
    print("Starting the image processing pipeline...")

    load_roboflow_workspace_and_project()

    if args.step == 'all':
        steps = [
            'resize_drawers', 'infer_drawers', 'crop_trays', 'resize_trays',
            'transcribe_labels_and_ids', 'infer_trays', 'crop_specimens', 'infer_beetles',
            'create_masks', 'infer_patterns', 'create_patterncsv', 'write_lengths', 'merge_datasets'
        ]
        for step in steps:
            run_step(step, directories, args)
    else:
        run_step(args.step, directories, args)

    print("Image processing pipeline completed.")
