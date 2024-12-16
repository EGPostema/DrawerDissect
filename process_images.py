import os
import time
import argparse
import roboflow
import asyncio
import aiofiles
from functions.resize_drawer import resize_drawer_images
from functions.process_metadata import process_files
from functions.infer_drawers import infer_drawers
from functions.crop_trays import crop_trays_from_fullsize
from functions.resize_trays import resize_tray_images
from functions.infer_labels import infer_tray_labels
from functions.crop_labels import crop_labels
from functions.infer_trays import infer_tray_images
from functions.crop_specimens import crop_specimens_from_trays
from functions.infer_beetles import infer_beetles
from functions.create_masks import create_masks
from functions.multipolygon_fixer import fix_mask
from functions.measure import generate_csv_with_visuals_and_measurements
from functions.censor_background import censor_background
from functions.infer_pins import infer_pins
from functions.create_pinmask import create_pinmask
from functions.create_transparency import create_transparency
from functions.ocr_label import transcribe_images, ImageProcessor, ProcessingResult
from functions.ocr_validation import validate_transcriptions
from functions.ocr_header import process_images, TranscriptionConfig, BARCODE_CONFIG, LABEL_CONFIG

# Set base directory
base_dir = os.path.abspath(os.path.dirname(__file__))

# User inputs for API keys and model details **MAKE SURE TO MODIFY THIS!**
ANTHROPIC_KEY = 'YOUR_API_HERE'
API_KEY = 'YOUR_ROBOFLOW_API_HERE'
WORKSPACE = 'YOUR_WORKSPACE_HERE'

# Metadata toggle
PROCESS_METADATA = 'N'  # Default is N; set to Y for FMNH users with Gigamacro TXT files

# Transcription toggles
TRANSCRIBE_BARCODES = 'Y'  # Default is Y; set to N if your drawer images DON'T have trays with barcoded labels
TRANSCRIBE_TAXONOMY = 'Y'  # Default is Y; set to N if your drawer images DON'T have trays seperated by taxon

# Initialize Roboflow
rf = roboflow.Roboflow(api_key=API_KEY)
workspace = rf.workspace(WORKSPACE)

# Default FMNH roboflow models, up-to-date as of Dec-16-2024
## All model names and versions adjustable
DRAWER_MODEL_ENDPOINT = 'trayfinder'
DRAWER_MODEL_VERSION = 8 
TRAY_MODEL_ENDPOINT = 'beetlefinder'
TRAY_MODEL_VERSION = 8
LABEL_MODEL_ENDPOINT = 'labelfinder'
LABEL_MODEL_VERSION = 4
MASK_MODEL_ENDPOINT = 'bugmasker-base'
MASK_MODEL_VERSION = 1
PIN_MODEL_ENDPOINT = 'pinmasker'
PIN_MODEL_VERSION = 5

# Define directories
directories = {
    'fullsize': 'drawers/fullsize',
    'metadata': 'drawers/fullsize/capture_metadata',
    'resized': 'drawers/resized',
    'coordinates': 'drawers/resized/coordinates',
    'trays': 'drawers/trays',
    'resized_trays': 'drawers/resized_trays',
    'resized_trays_coordinates': 'drawers/resized_trays/coordinates',
    'label_coordinates': 'drawers/resized_trays/label_coordinates',
    'labels': 'drawers/labels',
    'specimens': 'drawers/specimens',
    'mask_coordinates': 'drawers/masks/mask_coordinates',
    'mask_png': 'drawers/masks/mask_png',
    'measurements': 'drawers/measurements',
    'no_background': 'drawers/masks/no_background',
    'pin_coordinates': 'drawers/masks/pin_coords',
    'full_masks': 'drawers/masks/full_masks',
    'transparencies': 'drawers/transparencies',
    'specimen_level': 'drawers/transcriptions/specimen_labels',
    'tray_level': 'drawers/transcriptions/tray_labels',
}

# Create directories if not already there!
for name, directory in directories.items():
    if not os.path.exists(directory):
        print(f"Creating directory: {directory}")
        os.makedirs(directory, exist_ok=True)

# Define roboflow
def load_roboflow_workspace_and_project():
    rf = roboflow.Roboflow(api_key=API_KEY)
    workspace = rf.workspace(WORKSPACE)

# Commands for running individual steps
def run_step(step, directories, args):
    print(f"Running step: {step}")

    if step == 'resize_drawers':
        resize_drawer_images(directories['fullsize'], directories['resized'])
        print(f"Resized drawers saved in {directories['resized']}")

    elif step == 'process_metadata':
        if PROCESS_METADATA == 'Y':
            metadata_dir = directories['metadata']
            image_dir = directories['fullsize']
            output_file = os.path.join(metadata_dir, 'sizeratios.csv')
        
            process_files(metadata_dir, image_dir, output_file)
            print(f"Metadata processed and results saved in {output_file}")
        else:
            print("Skipping metadata processing")

    elif step == 'infer_drawers':
        infer_drawers(
            directories['resized'], 
            directories['coordinates'], 
            API_KEY, 
            DRAWER_MODEL_ENDPOINT, 
            DRAWER_MODEL_VERSION, 
            confidence=args.drawer_confidence, 
            overlap=args.drawer_overlap
        )
        print(f"Tray bounding boxes saved in {directories['coordinates']}")
    
    elif step == 'crop_trays':
        crop_trays_from_fullsize(
            directories['fullsize'], 
            directories['resized'], 
            directories['trays']
        )
        print(f"Cropped trays saved in {directories['trays']}")
    
    elif step == 'resize_trays':
        resize_tray_images(directories['trays'], directories['resized_trays'])
        print(f"Resized tray images saved in {directories['resized_trays']}")

    elif step == 'infer_labels':
        infer_tray_labels(
            directories['resized_trays'], 
            directories['label_coordinates'], 
            API_KEY, 
            LABEL_MODEL_ENDPOINT, 
            LABEL_MODEL_VERSION, 
            confidence=args.label_confidence, 
            overlap=args.label_overlap
        )
        print(f"Label bounding boxes for all trays saved in {directories['label_coordinates']}")

    elif step == 'crop_labels':
        crop_labels(
            directories['trays'], 
            directories['resized_trays'], 
            directories['label_coordinates'], 
            directories['labels']
        )
        print(f"Cropped labels saved in {directories['labels']}")

    
    elif step == 'infer_trays':
        infer_tray_images(
            directories['resized_trays'], 
            directories['resized_trays_coordinates'], 
            API_KEY, 
            TRAY_MODEL_ENDPOINT, 
            TRAY_MODEL_VERSION, 
            confidence=args.tray_confidence, 
            overlap=args.tray_overlap
        )
        print(f"Specimen bounding boxes for all trays saved in {directories['resized_trays_coordinates']}")
    
    elif step == 'crop_specimens':
        crop_specimens_from_trays(
            directories['trays'], 
            directories['resized_trays'], 
            directories['specimens']
        )
        print(f"Cropped specimens saved in {directories['specimens']}")
    
    elif step == 'infer_beetles':
        infer_beetles(
            directories['specimens'], 
            directories['mask_coordinates'], 
            API_KEY, 
            MASK_MODEL_ENDPOINT, 
            MASK_MODEL_VERSION, 
            confidence=args.beetle_confidence
        )
        print(f"Segmentation mask coordinates saved in {directories['mask_coordinates']}")
    
    elif step == 'create_masks':
        create_masks(
            directories['mask_coordinates'], 
            directories['mask_png']
        )
        print(f"Mask .png files saved in {directories['mask_png']}")

    elif step == 'fix_mask':
        fix_mask(
            directories['mask_png']
        )
        print(f"Mask with duplicate polygons fixed and re-saved to {directories['mask_png']}")

    elif step == 'process_and_measure_images':
        sizeratios_path = os.path.join(directories['metadata'], 'sizeratios.csv')
        
        # If PROCESS_METADATA is 'N', pass None instead of the sizeratios.csv path
        metadata_file = sizeratios_path if PROCESS_METADATA == 'Y' else None
        
        generate_csv_with_visuals_and_measurements(
            directories['specimens'],
            directories['mask_png'],
            metadata_file,
            directories['measurements']
        )
        print(f"Measurements and visuals saved in {directories['measurements']}")

    elif step == 'censor_background':
        censor_background(
            directories['specimens'], 
            directories['mask_png'], 
            directories['no_background'], 
            os.path.join(directories['measurements'], 'measurements.csv')
        )
        print(f"Images with censored backgrounds saved in {directories['no_background']}")
        
    elif step == 'infer_pins':
        infer_pins(
            directories['no_background'], 
            directories['pin_coordinates'],
            os.path.join(directories['measurements'], 'measurements.csv'),
            API_KEY, 
            PIN_MODEL_ENDPOINT, 
            PIN_MODEL_VERSION, 
            confidence=args.pin_confidence
        )
        print(f"Pin mask coordinates saved in {directories['pin_coordinates']}")

    elif step == 'create_pinmask':
        create_pinmask(
            directories['mask_png'], 
            directories['pin_coordinates'], 
            directories['full_masks']
        )
        print(f"Masks with pins saved in {directories['full_masks']}")


    elif step == 'create_transparency':
        create_transparency(
            directories['specimens'],
            directories['full_masks'],
            directories['transparencies']
        )
        print(f"All specimen transparencies saved in {directories['transparencies']}")

    elif step == 'transcribe_images':
        asyncio.run(transcribe_images(
            directories['specimens'],
            os.path.join(directories['specimen_level'], 'location_frags.csv'),
            ANTHROPIC_KEY
        ))
        print(f"Label reconstruction completed. Results saved to {directories['specimen_level']}")

    elif step == 'validate_transcription':
        asyncio.run(validate_transcriptions(
            os.path.join(directories['specimen_level'], 'location_frags.csv'),
            os.path.join(directories['specimen_level'], 'location_checked.csv'),
            ANTHROPIC_KEY
        ))
        print(f"Location validation completed. Results saved to {directories['specimen_level']}/location_checked.csv")

    elif step == 'process_barcodes':
        if TRANSCRIBE_BARCODES == 'Y':
            asyncio.run(process_images(
                directories['labels'],
                os.path.join(directories['tray_level'], 'unit_barcodes.csv'),
                ANTHROPIC_KEY,
                BARCODE_CONFIG
            ))
            print(f"Barcode processing completed. Results saved to {directories['tray_level']}")
        else:
            print("Skipping barcode transcription as per configuration")
    
    elif step == 'transcribe_taxonomy':
        if TRANSCRIBE_TAXONOMY == 'Y':
            asyncio.run(process_images(
                directories['labels'],
                os.path.join(directories['tray_level'], 'taxonomy.csv'),
                ANTHROPIC_KEY,
                LABEL_CONFIG
            ))
            print(f"Taxonomic label transcription completed. Results saved to {directories['tray_level']}")
        else:
            print("Skipping taxonomy transcription as per configuration")
    
    else:
        print(f"Unknown step: {step}")

def main():
    start_time = time.time()
    
    all_steps = [
        'resize_drawers', 'process_metadata', 'infer_drawers', 'crop_trays',
        'resize_trays', 'infer_labels', 'crop_labels', 'infer_trays',
        'crop_specimens', 'infer_beetles', 'create_masks', 'fix_mask',
        'process_and_measure_images', 'censor_background', 'infer_pins',
        'create_pinmask', 'create_transparency', 'transcribe_images', 'validate_transcription', 'process_barcodes', 
        'transcribe_taxonomy'
    ]
    
    parser = argparse.ArgumentParser(description="Process images with specified steps and parameters.")
    
    parser.add_argument(
        'steps',
        nargs='+',  # Changed from '?' to '+' to accept multiple steps
        choices=all_steps + ['all'],
        help="Steps to execute"
    )
    
    for step in all_steps:
        parser.add_argument(
            f'--skip_{step}',
            action='store_true',
            help=f"Skip the {step} step"
        )
    
    parser.add_argument('--drawer_confidence', type=int, default=50)
    parser.add_argument('--drawer_overlap', type=int, default=50)
    parser.add_argument('--tray_confidence', type=int, default=50)
    parser.add_argument('--tray_overlap', type=int, default=50)
    parser.add_argument('--label_confidence', type=int, default=50)
    parser.add_argument('--label_overlap', type=int, default=50)
    parser.add_argument('--beetle_confidence', type=int, default=50)
    parser.add_argument('--pin_confidence', type=int, default=50)
    
    args = parser.parse_args()
    print("Starting the image processing pipeline...")
    load_roboflow_workspace_and_project()

    if 'all' in args.steps:
        # Run all steps
        for step in all_steps:
            if not getattr(args, f'skip_{step}'):
                step_start = time.time()
                run_step(step, directories, args)
                step_time = time.time() - step_start
                print(f"{step} completed in {step_time:.2f} seconds")
    else:
        # Run specified steps in order
        for step in args.steps:
            step_start = time.time()
            run_step(step, directories, args)
            step_time = time.time() - step_start
            print(f"{step} completed in {step_time:.2f} seconds")

    total_time = time.time() - start_time
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    seconds = total_time % 60
    print(f"\nTotal processing time: {hours}h {minutes}m {seconds:.2f}s")

if __name__ == '__main__':
    main()
