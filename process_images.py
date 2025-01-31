# Imports
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
from functions.specimen_guide import create_specimen_guides
from functions.infer_beetles import infer_beetles
from functions.create_masks import create_masks
from functions.multipolygon_fixer import fix_mask
from functions.measure import generate_csv_with_measurements
from functions.measure import visualize_measurements
from functions.censor_background import censor_background
from functions.infer_pins import infer_pins
from functions.create_pinmask import create_pinmask
from functions.create_transparency import create_transparency
from functions.ocr_label import transcribe_images, ImageProcessor, ProcessingResult
from functions.ocr_validation import validate_transcriptions
from functions.ocr_header import process_images, TranscriptionConfig, BARCODE_CONFIG, LABEL_CONFIG
from functions.merge_data import merge_data

# Set base directory
base_dir = os.path.abspath(os.path.dirname(__file__))

# User inputs for API keys **MAKE SURE TO MODIFY THIS!**
ANTHROPIC_KEY = 'ANTHROPIC_API_HERE'
ROBOFLOW_KEY = 'ROBOFLOW_API_HERE'

# Default FMNH roboflow models, up-to-date as of Jan-16-2025
WORKSPACE = 'field-museum'

DRAWER_MODEL_ENDPOINT = 'trayfinder-labels'
DRAWER_MODEL_VERSION = 17 
TRAY_MODEL_ENDPOINT = 'bugfinder-kdn9e'
TRAY_MODEL_VERSION = 9
LABEL_MODEL_ENDPOINT = 'labelfinder'
LABEL_MODEL_VERSION = 5
MASK_MODEL_ENDPOINT = 'bugmasker-all'
MASK_MODEL_VERSION = 1
PIN_MODEL_ENDPOINT = 'pinmasker'
PIN_MODEL_VERSION = 5

# Toggles
PROCESS_METADATA = 'N'  # Default is N; set to Y for FMNH users with Gigamacro TXT files
TRANSCRIBE_BARCODES = 'Y'  # Default is Y; set to N if your drawer images DON'T have trays with barcoded labels
TRANSCRIBE_TAXONOMY = 'Y'  # Default is Y; set to N if your drawer images DON'T have trays seperated by taxon
PIPELINE_MODE = 'Default' # For the final data-merging pipeline; for test image, change to 'FMNH'

# Define all directories
directories = {
    'fullsize': 'drawers/fullsize',
    'metadata': 'drawers/fullsize/capture_metadata',
    'resized': 'drawers/resized',
    'coordinates': 'drawers/resized/coordinates',
    'trays': 'drawers/trays',
    'guides': 'drawers/guides',
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
    'whitebg_specimens': 'drawers/whitebg_specimens',
    'specimen_level': 'drawers/transcriptions/specimen_labels',
    'tray_level': 'drawers/transcriptions/tray_labels',
    'data': 'drawers/data'
}

# Create directories if not already there!
for name, directory in directories.items():
    if not os.path.exists(directory):
        print(f"Creating directory: {directory}")
        os.makedirs(directory, exist_ok=True)

# Single instance of Roboflow initialization
def get_roboflow_instance():
    if not hasattr(get_roboflow_instance, '_rf_instance'):
        print("Initializing Roboflow workspace (this should only happen once)")
        get_roboflow_instance._rf_instance = roboflow.Roboflow(api_key=ROBOFLOW_KEY)
        get_roboflow_instance._workspace_instance = get_roboflow_instance._rf_instance.workspace(WORKSPACE)
    return get_roboflow_instance._rf_instance, get_roboflow_instance._workspace_instance

# Commands for running individual steps
def run_step(step, directories, args, rf_instance, workspace_instance):
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

    elif step == 'find_trays':
        infer_drawers(
            directories['resized'], 
            directories['coordinates'], 
            rf_instance,
            workspace_instance, 
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
        resize_tray_images(directories['trays'], 
        directories['resized_trays']
        )
        print(f"Resized tray images saved in {directories['resized_trays']}")

    elif step == 'find_traylabels':
        infer_tray_labels(
            directories['resized_trays'], 
            directories['label_coordinates'], 
            rf_instance,
            workspace_instance, 
            LABEL_MODEL_ENDPOINT, 
            LABEL_MODEL_VERSION, 
            confidence=args.label_confidence, 
            overlap=args.label_overlap
        )
        print(f"Tray label bounding boxes saved in {directories['label_coordinates']}")

    elif step == 'crop_labels':
        crop_labels(
            directories['trays'], 
            directories['resized_trays'], 
            directories['label_coordinates'], 
            directories['labels']
        )
        print(f"Cropped labels saved in {directories['labels']}")
    
    elif step == 'find_specimens':
        infer_tray_images(
            directories['resized_trays'], 
            directories['resized_trays_coordinates'], 
            rf_instance,
            workspace_instance, 
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

    elif step == 'create_traymaps':
        create_specimen_guides(
            directories['trays'],
            directories['resized_trays'],
            directories['guides']
        )
        print(f"Specimen maps saved in {directories['guides']}")
    
    elif step == 'outline_specimens':
        infer_beetles(
            directories['specimens'], 
            directories['mask_coordinates'], 
            rf_instance,
            workspace_instance, 
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

    elif step == 'fix_masks':
        fix_mask(
            directories['mask_png']
        )
        print(f"Fixed masks saved in {directories['mask_png']}")

    elif step == 'measure_specimens':
        sizeratios_path = os.path.join(directories['metadata'], 'sizeratios.csv')
        metadata_file = sizeratios_path if PROCESS_METADATA == 'Y' else None

        # Generate measurements and save CSV
        generate_csv_with_measurements(
            directories['mask_png'],
            metadata_file,
            directories['measurements']
        )

    elif step == 'censor_background':
        censor_background(
            directories['specimens'], 
            directories['mask_png'], 
            directories['no_background'], 
            os.path.join(directories['measurements'], 'measurements.csv')
        )
        print(f"Images with censored backgrounds saved in {directories['no_background']}")
        
    elif step == 'outline_pins':
        infer_pins(
            directories['no_background'], 
            directories['pin_coordinates'],
            os.path.join(directories['measurements'], 'measurements.csv'), 
            rf_instance,
            workspace_instance, 
            PIN_MODEL_ENDPOINT, 
            PIN_MODEL_VERSION, 
            confidence=args.pin_confidence
        )
        print(f"Pin coordinates saved in {directories['pin_coordinates']}")

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
            directories['transparencies'],
            directories['whitebg_specimens']
        )
        print(f"All finished specimen photos saved in {directories['transparencies']} and {directories['whitebg_specimens']}")

    elif step == 'transcribe_speclabels':
        asyncio.run(transcribe_images(
            directories['specimens'],
            os.path.join(directories['specimen_level'], 'location_frags.csv'),
            ANTHROPIC_KEY
        ))
        print(f"Label reconstruction completed. Results saved to {directories['specimen_level']}")

    elif step == 'validate_speclabels':
        asyncio.run(validate_transcriptions(
            os.path.join(directories['specimen_level'], 'location_frags.csv'),
            os.path.join(directories['specimen_level'], 'location_checked.csv'),
            ANTHROPIC_KEY
        ))
        print(f"Location validation completed. Results saved to {directories['specimen_level']}/location_checked.csv")

    elif step == 'transcribe_barcodes':
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

    elif step == 'merge_data':
        output_base_path = os.path.join(directories['data'], 'merged_data')
        merge_data(
            os.path.join(directories['measurements'], 'measurements.csv'),
            os.path.join(directories['specimen_level'], 'location_checked.csv'),
            os.path.join(directories['tray_level'], 'taxonomy.csv'),
            os.path.join(directories['tray_level'], 'unit_barcodes.csv'),
            output_base_path,
            mode=PIPELINE_MODE
        )
        print(f"Merged dataset saved with a timestamped filename in {directories['data']}")

    else:
        print(f"Unknown step: {step}")

def main():
    start_time = time.time()
    
    # Get single Roboflow instance at the start with specified workspace
    rf_instance, workspace_instance = get_roboflow_instance()
    
    all_steps = [
        'resize_drawers', 'process_metadata', 'find_trays', 'crop_trays',
        'resize_trays', 'find_traylabels', 'crop_labels', 'find_specimens',
        'crop_specimens', 'create_traymaps', 'outline_specimens', 'create_masks', 'fix_masks',
        'measure_specimens', 'censor_background', 'outline_pins',
        'create_pinmask', 'create_transparency', 'transcribe_speclabels', 'validate_speclabels', 'transcribe_barcodes', 
        'transcribe_taxonomy', 'merge_data'
    ]
    
    parser = argparse.ArgumentParser(description="Process images with specified steps and parameters.")
    
    parser.add_argument(
        'steps',
        nargs='+',
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

    if 'all' in args.steps:
        # Run all steps
        for step in all_steps:
            if not getattr(args, f'skip_{step}'):
                step_start = time.time()
                run_step(step, directories, args, rf_instance, workspace_instance)
                step_time = time.time() - step_start
                print(f"{step} completed in {step_time:.2f} seconds")
    else:
        # Run specified steps in order
        for step in args.steps:
            step_start = time.time()
            run_step(step, directories, args, rf_instance, workspace_instance)
            step_time = time.time() - step_start
            print(f"{step} completed in {step_time:.2f} seconds")

    total_time = time.time() - start_time
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    seconds = total_time % 60
    print(f"\nTotal processing time: {hours}h {minutes}m {seconds:.2f}s")

if __name__ == '__main__':
    main()
