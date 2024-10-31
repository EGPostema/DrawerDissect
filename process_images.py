import os
import argparse
import roboflow
from functions.resize_drawer import resize_drawer_images
from functions.infer_drawers import infer_drawers
from functions.crop_trays import crop_trays_from_fullsize
from functions.resize_trays import resize_tray_images
from functions.infer_labels import infer_labels
from functions.crop_labelinfo import crop_info_from_trays
from functions.infer_trays import infer_tray_images
from functions.crop_specimens import crop_specimens_from_trays
from functions.infer_beetles import infer_beetles
from functions.create_masks import create_masks
from functions.measure import process_and_measure_images
from functions.mask_specimens import mask_specimens
from functions.infer_patterns import infer_patterns
from functions.pattern_csv import create_patterncsv
from functions.merge_data import merge_datasets

# Set base directory
base_dir = os.path.abspath(os.path.dirname(__file__))

# User inputs for API key and model details **MAKE SURE TO MODIFY THIS!**
API_KEY = 'API_KEY'
WORKSPACE = 'field-museum'

# Initialize Roboflow
rf = roboflow.Roboflow(api_key=API_KEY)
workspace = rf.workspace(WORKSPACE)

# User inputs for roboflow models **MAKE SURE TO MODIFY THESE!**
DRAWER_MODEL_ENDPOINT = 'trayfinder'
DRAWER_MODEL_VERSION = 9  # Adjust the version as needed!
TRAY_MODEL_ENDPOINT = 'beetlefinder'
TRAY_MODEL_VERSION = 8  # Adjust the version as needed
LABEL_MODEL_ENDPOINT = 'labelfinder'
LABEL_MODEL_VERSION = 5  # Adjust the version as needed!
MASK_MODEL_ENDPOINT = 'beetlemasker'
MASK_MODEL_VERSION = 9  # Adjust the version as needed!
PATTERN_MODEL_ENDPOINT = 'maculator'
PATTERN_MODEL_VERSION = 5  # Adjust the version as needed!

# Define directories
directories = {
    'fullsize': 'drawers/fullsize_drawers',
    'resized': 'drawers/resized_drawers',
    'coordinates': 'drawers/resized/coordinates',
    'trays': 'drawers/trays',
    'resized_trays': 'drawers/resized_trays',
    'resized_trays_coordinates': 'drawers/resized_trays/coordinates',
    'label_coordinates': 'drawers/labels/label_coordinates',
    'barcodes': 'drawers/labels/barcode_crops',
    'specimens': 'drawers/specimens',
    'mask_coordinates': 'drawers/masks/mask_coordinates',
    'mask_csv': 'drawers/masks/mask_csv',
    'mask_png': 'drawers/masks/mask_png',
    'masked_specs': 'drawers/masked_specs',
    'lengths': 'drawers/specimens/lengths',
    'pattern_jsons': 'drawers/patterns/pattern_jsons',
    'pattern_data': 'drawers/patterns/pattern_data',
    'merged_data': 'drawers/data'
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

# Define background color for segmented specimens (white or black); default is white
background_color = 'white'

# Commands for running individual steps
def run_step(step, directories, args):
    print(f"Running step: {step}")

    if step == 'resize_drawers':
        resize_drawer_images(directories['fullsize'], directories['resized'])
        print(f"Resized drawers saved in {directories['resized']}")

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
        infer_labels(
            directories['resized_trays'], 
            directories['label_coordinates'], 
            API_KEY, 
            LABEL_MODEL_ENDPOINT, 
            LABEL_MODEL_VERSION, 
            confidence=args.label_confidence, 
            overlap=args.label_overlap
        )
        print(f"Label bounding boxes saved in {directories['label_coordinates']}")

    elif step == 'crop_labelinfo':
        crop_info_from_trays(
            directories['trays'], 
            directories['resized_trays'], 
            directories['barcodes']
        )
        print(f"Cropped barcodes saved in {directories['barcodes']}")

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
        create_masks(directories['mask_coordinates'], directories['mask_csv'], directories['mask_png'])
        print(f"Mask .csv files saved in {directories['mask_csv']}")
        print(f"Mask .png files saved in {directories['mask_png']}")

    elif step == 'mask_specimens':
        mask_specimens(
            directories['specimens'], 
            directories['mask_png'], 
            directories['masked_specs'], 
            background=background_color
        )
        print(f"Masked specimens saved in {directories['masked_specs']}")

    elif step == 'infer_patterns':
        infer_patterns(
            directories['specimens'], 
            directories['pattern_jsons'], 
            API_KEY, 
            PATTERN_MODEL_ENDPOINT, 
            PATTERN_MODEL_VERSION
        )
        print(f"Pattern inferences saved in {directories['pattern_jsons']}")

    elif step == 'create_patterncsv':
        create_patterncsv(
            directories['pattern_jsons'], 
            os.path.join(directories['pattern_data'], 'pattern_data.csv')
        )
        print(f"Pattern data csv saved in {directories['pattern_data']}")

    elif step == 'process_and_measure_images':
        process_and_measure_images(
            directories['mask_png'], 
            os.path.join(directories['lengths'], 'lengths.csv')
        )
        print(f"Mask measurements saved in {os.path.join(directories['lengths'], 'lengths.csv')}")

    elif step == 'merge_datasets':
        merge_datasets(
            directories['merged_data'] + '/coloroptera_data.csv',            
            directories['lengths'] + '/lengths.csv',               
            directories['pattern_data'] + '/pattern_data.csv',     
            directories['merged_data']
        )
        print(f"Merged datasets and saved in {directories['merged_data'] + '/coloroptera_data.csv'}")

    else:
        print(f"Unknown step: {step}")

# Use argparse to allow individual steps to be called (see README for commands)
def main():
    parser = argparse.ArgumentParser(
        description="Process images with specified confidence and overlap."
    )
    
    parser.add_argument(
        'step', 
        nargs='?', 
        choices=[
            'all', 
            'resize_drawers', 
            'infer_drawers', 
            'crop_trays', 
            'resize_trays', 
            'infer_labels', 
            'crop_labelinfo', 
            'infer_trays', 
            'crop_specimens', 
            'infer_beetles', 
            'create_masks', 
            'mask_specimens', 
            'infer_patterns', 
            'create_patterncsv', 
            'process_and_measure_images', 
            'merge_datasets'
        ],
        default='all', 
        help="Step to execute"
    )
    
    parser.add_argument(
        '--drawer_confidence', 
        type=int, 
        default=50, 
        help="Confidence level for finding trays in drawers. Default is 50."
    )
    parser.add_argument(
        '--drawer_overlap', 
        type=int, 
        default=50, 
        help="Overlap level of trays in drawers. Default is 50."
    )
    parser.add_argument(
        '--tray_confidence', 
        type=int, 
        default=50, 
        help="Confidence level for finding specimens in trays. Default is 50."
    )
    parser.add_argument(
        '--tray_overlap', 
        type=int, 
        default=50, 
        help="Overlap level for specimens in trays. Default is 50."
    )
    parser.add_argument(
        '--label_confidence', 
        type=int, 
        default=50, 
        help="Confidence level for finding tray labels. Default is 50."
    )
    parser.add_argument(
        '--label_overlap', 
        type=int, 
        default=50, 
        help="Overlap level for tray labels. Default is 50."
    )
    parser.add_argument(
        '--beetle_confidence', 
        type=int, 
        default=50, 
        help="Confidence level for specimen masks. Default is 50."
    )
    
    args = parser.parse_args()

    # Let's process some images!
    print("Starting the image processing pipeline...")

    load_roboflow_workspace_and_project()

    if args.step == 'all':
        steps = [
            'resize_drawers', 
            'infer_drawers', 
            'crop_trays', 
            'resize_trays', 
            'infer_labels', 
            'crop_labelinfo', 
            'infer_trays', 
            'crop_specimens', 
            'infer_beetles', 
            'create_masks', 
            'mask_specimens', 
            'infer_patterns', 
            'create_patterncsv', 
            'process_and_measure_images', 
            'merge_datasets'
        ]
        
        for step in steps:
            run_step(step, directories, args)
    else:
        run_step(args.step, directories, args)

    print("Image processing pipeline completed.")


if __name__ == "__main__":
    main()