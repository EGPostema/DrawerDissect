# Imports
import os
import time
import argparse
import roboflow
import asyncio
import shutil
import csv
from datetime import datetime
from functools import lru_cache
from typing import Tuple, Dict, Any
from config import DrawerDissectConfig
from logging_utils import log, StepTimer
from functions.drawer_management import get_drawers_to_process, validate_drawer_structure, discover_and_sort_drawers, is_specimen_only_drawer
from functions.resize_drawer import resize_drawer_images
from functions.infer_color import infer_color
from functions.infer_drawers import infer_drawers
from functions.crop_color import crop_color_from_fullsize
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
from functions.censor_background import censor_background
from functions.infer_pins import infer_pins
from functions.create_pinmask import create_pinmask
from functions.create_transparency import create_transparency
from functions.ocr_header import process_image_folder
from functions.ocr_label import process_specimen_labels
from functions.ocr_validation import validate_transcriptions
from functions.merge_data import merge_data

# Only activate roboflow when needed (lazy loading)
@lru_cache(maxsize=1)
def get_roboflow_instance(config) -> Tuple[roboflow.Roboflow, roboflow.Workspace]:
    """Initialize Roboflow API connection."""
    log("Initializing Roboflow API connection")
    rf_instance = roboflow.Roboflow(api_key=config.api_keys['roboflow'])
    workspace_instance = rf_instance.workspace(config.workspace)
    return rf_instance, workspace_instance

# Defining all steps
def run_step_for_drawer(step, config, drawer_id, args, rf_instance=None, workspace_instance=None):
    """Run a specific pipeline step for a specific drawer."""
    with StepTimer(f"{step}_{drawer_id}"):
        # Get memory management settings for this step from config
        mem_config = config.get_memory_config(step)
        
        # Command-line args override config settings
        sequential = args.sequential if args.sequential is not None else mem_config.get('sequential', False)
        max_workers = args.max_workers if args.max_workers is not None else mem_config.get('max_workers')
        batch_size = args.batch_size if args.batch_size is not None else mem_config.get('batch_size')
        
        # Log memory management settings if they're non-default
        if sequential or max_workers is not None or batch_size is not None:
            log(f"Memory settings: sequential={sequential}, max_workers={max_workers}, batch_size={batch_size}")
        
        if step in {'find_color','find_trays', 'find_traylabels', 'find_specimens', 
                    'outline_specimens', 'outline_pins'} and not rf_instance:
                rf_instance, workspace_instance = get_roboflow_instance(config)
                
        if step == 'resize_drawers':
            resize_drawer_images(
                config.get_drawer_directory(drawer_id, 'fullsize'), 
                config.get_drawer_directory(drawer_id, 'resized'),
                sequential=sequential,
                max_workers=max_workers,
                batch_size=batch_size
            )
        
        elif step == 'find_color':
            color_model = config.roboflow_models['color']
            infer_color(
                config.get_drawer_directory(drawer_id, 'resized'),
                config.get_drawer_directory(drawer_id, 'color_coordinates'),
                rf_instance,
                workspace_instance,
                color_model['endpoint'],
                color_model['version'],
                confidence=args.color_confidence or color_model['confidence'],
                overlap=args.color_overlap or color_model['overlap']
            )

        elif step == 'crop_color':
            crop_color_from_fullsize(
                config.get_drawer_directory(drawer_id, 'fullsize'),
                config.get_drawer_directory(drawer_id, 'resized'),
                config.get_drawer_directory(drawer_id, 'colorstandard'),
                sequential=sequential,
                max_workers=max_workers,
                batch_size=batch_size
            )
        

        elif step == 'find_trays':
            drawer_model = config.roboflow_models['drawer']
            infer_drawers(
                config.get_drawer_directory(drawer_id, 'resized'),
                config.get_drawer_directory(drawer_id, 'coordinates'),
                rf_instance,
                workspace_instance,
                drawer_model['endpoint'],
                drawer_model['version'],
                confidence=args.drawer_confidence or drawer_model['confidence'],
                overlap=args.drawer_overlap or drawer_model['overlap']
            )
        
        elif step == 'crop_trays':
            crop_trays_from_fullsize(
                config.get_drawer_directory(drawer_id, 'fullsize'),
                config.get_drawer_directory(drawer_id, 'resized'),
                config.get_drawer_directory(drawer_id, 'trays'),
                sequential=sequential,
                max_workers=max_workers,
                batch_size=batch_size
            )
        
        elif step == 'resize_trays':
            resize_tray_images(
                config.get_drawer_directory(drawer_id, 'trays'),
                config.get_drawer_directory(drawer_id, 'resized_trays')
            )
        
        elif step == 'find_traylabels':
            label_model = config.roboflow_models['label']
            infer_tray_labels(
                config.get_drawer_directory(drawer_id, 'resized_trays'),
                config.get_drawer_directory(drawer_id, 'label_coordinates'),
                rf_instance,
                workspace_instance,
                label_model['endpoint'],
                label_model['version'],
                confidence=args.label_confidence or label_model['confidence'],
                overlap=args.label_overlap or label_model['overlap']
            )
        
        elif step == 'crop_labels':
            crop_labels(
                config.get_drawer_directory(drawer_id, 'trays'),
                config.get_drawer_directory(drawer_id, 'resized_trays'),
                config.get_drawer_directory(drawer_id, 'label_coordinates'),
                config.get_drawer_directory(drawer_id, 'labels')
            )
        
        elif step == 'find_specimens':
            tray_model = config.roboflow_models['tray']
            infer_tray_images(
                config.get_drawer_directory(drawer_id, 'resized_trays'),
                config.get_drawer_directory(drawer_id, 'resized_trays_coordinates'),
                rf_instance,
                workspace_instance,
                tray_model['endpoint'],
                tray_model['version'],
                confidence=args.tray_confidence or tray_model['confidence'],
                overlap=args.tray_overlap or tray_model['overlap']
            )
        
        elif step == 'crop_specimens':
            crop_specimens_from_trays(
                config.get_drawer_directory(drawer_id, 'trays'),
                config.get_drawer_directory(drawer_id, 'resized_trays'),
                config.get_drawer_directory(drawer_id, 'specimens')
            )
        
        elif step == 'create_traymaps':
            create_specimen_guides(
                config.get_drawer_directory(drawer_id, 'resized_trays'),
                config.get_drawer_directory(drawer_id, 'guides')
            )
        
        elif step == 'outline_specimens':
            mask_model = config.roboflow_models['mask']
            infer_beetles(
                config.get_drawer_directory(drawer_id, 'specimens'),
                config.get_drawer_directory(drawer_id, 'mask_coordinates'),
                rf_instance,
                workspace_instance,
                mask_model['endpoint'],
                mask_model['version'],
                confidence=args.beetle_confidence or mask_model['confidence'],
                max_workers=max_workers,
                sequential=sequential
            )
        
        elif step == 'create_masks':
            create_masks(
                config.get_drawer_directory(drawer_id, 'mask_coordinates'),
                config.get_drawer_directory(drawer_id, 'mask_png')
            )
        
        elif step == 'fix_masks':
            fix_mask(config.get_drawer_directory(drawer_id, 'mask_png'))
        
        elif step == 'measure_specimens':            
            generate_csv_with_measurements(
                config.get_drawer_directory(drawer_id, 'mask_png'),
                config.get_drawer_directory(drawer_id, 'measurements'),
                visualization_mode=config.processing_flags.get('measurement_visualizations', 'on')
            )
        
        elif step == 'censor_background':
            censor_background(
                config.get_drawer_directory(drawer_id, 'specimens'),
                config.get_drawer_directory(drawer_id, 'mask_png'),
                config.get_drawer_directory(drawer_id, 'no_background')
            )
        
        elif step == 'outline_pins':
            pin_model = config.roboflow_models['pin']
            infer_pins(
                config.get_drawer_directory(drawer_id, 'no_background'),
                config.get_drawer_directory(drawer_id, 'pin_coordinates'),
                os.path.join(config.get_drawer_directory(drawer_id, 'measurements'), 'measurements.csv'),
                rf_instance,
                workspace_instance,
                pin_model['endpoint'],
                pin_model['version'],
                confidence=args.pin_confidence or pin_model['confidence'],
                sequential=sequential,
                max_workers=max_workers
            )
        
        elif step == 'create_pinmask':
            create_pinmask(
                config.get_drawer_directory(drawer_id, 'mask_png'),
                config.get_drawer_directory(drawer_id, 'pin_coordinates'),
                config.get_drawer_directory(drawer_id, 'full_masks')
            )
        
        elif step == 'create_transparency':
            create_transparency(
                config.get_drawer_directory(drawer_id, 'no_background'),
                config.get_drawer_directory(drawer_id, 'full_masks'),
                config.get_drawer_directory(drawer_id, 'transparencies'),
                config.get_drawer_directory(drawer_id, 'whitebg_specimens'),
                sequential=sequential,
                max_workers=max_workers,
                batch_size=batch_size
            )
        
        elif step == 'transcribe_speclabels':
            if config.processing_flags['transcribe_specimen_labels']:
                prompts = {
                    'transcription': config.prompts['specimen_label'],
                    'location': config.prompts['location']
                }
                asyncio.run(process_specimen_labels(
                    config.get_drawer_directory(drawer_id, 'specimens'),
                    os.path.join(config.get_drawer_directory(drawer_id, 'specimen_level'), 'location_frags.csv'),
                    config.api_keys['anthropic'],
                    prompts=prompts,
                    model_config=config.claude_config
                ))
            else:
                log("Specimen label transcription disabled in config - skipping")
        
        elif step == 'validate_speclabels':
            if config.processing_flags['transcribe_specimen_labels']:
                prompts = {
                    'system': config.prompts['validation']['system'],
                    'user': config.prompts['validation']['user']
                }
                asyncio.run(validate_transcriptions(
                    os.path.join(config.get_drawer_directory(drawer_id, 'specimen_level'), 'location_frags.csv'),
                    os.path.join(config.get_drawer_directory(drawer_id, 'specimen_level'), 'location_checked.csv'),
                    config.api_keys['anthropic'],
                    prompts=prompts,
                    model_config=config.claude_config
                ))
            else:
                log("Specimen label validation skipped (transcription disabled)")

        elif step == 'transcribe_barcodes':
            if config.processing_flags['transcribe_barcodes']:
                prompts = {
                    'system': config.prompts['barcode']['system'],
                    'user': config.prompts['barcode']['user']
                }
                asyncio.run(process_image_folder(
                    config.get_drawer_directory(drawer_id, 'labels'),
                    os.path.join(config.get_drawer_directory(drawer_id, 'tray_level'), 'unit_barcodes.csv'),
                    config.api_keys['anthropic'],
                    prompts=prompts,
                    model_config=config.claude_config
                ))
            else:
                log("Barcode transcription disabled in config - skipping")

        elif step == 'transcribe_geocodes':
            if config.processing_flags['transcribe_geocodes']:
                prompts = {
                    'system': config.prompts['geocode']['system'],
                    'user': config.prompts['geocode']['user']
                }
                asyncio.run(process_image_folder(
                    config.get_drawer_directory(drawer_id, 'labels'),
                    os.path.join(config.get_drawer_directory(drawer_id, 'tray_level'), 'geocodes.csv'),
                    config.api_keys['anthropic'],
                    prompts=prompts,
                    model_config=config.claude_config
                ))

        elif step == 'transcribe_taxonomy':
            if config.processing_flags['transcribe_taxonomy']:
                prompts = {
                    'system': config.prompts['taxonomy']['system'],
                    'user': config.prompts['taxonomy']['user']
                }
                asyncio.run(process_image_folder(
                    config.get_drawer_directory(drawer_id, 'labels'),
                    os.path.join(config.get_drawer_directory(drawer_id, 'tray_level'), 'taxonomy.csv'),
                    config.api_keys['anthropic'],
                    prompts=prompts,
                    model_config=config.claude_config
                ))
            else:
                log("Taxonomy transcription disabled in config - skipping")
        
        elif step == 'merge_data':
            specimens_dir = config.get_drawer_directory(drawer_id, 'specimens')
            measurements_path = os.path.join(config.get_drawer_directory(drawer_id, 'measurements'), 'measurements.csv')
            location_checked_path = os.path.join(config.get_drawer_directory(drawer_id, 'specimen_level'), 'location_checked.csv')
            taxonomy_path = os.path.join(config.get_drawer_directory(drawer_id, 'tray_level'), 'taxonomy.csv')
            unit_barcodes_path = os.path.join(config.get_drawer_directory(drawer_id, 'tray_level'), 'unit_barcodes.csv')
            geocodes_path = os.path.join(config.get_drawer_directory(drawer_id, 'tray_level'), 'geocodes.csv')
            labels_dir = config.get_drawer_directory(drawer_id, 'labels')
            output_base_path = os.path.join(config.get_drawer_directory(drawer_id, 'data'), 'merged_data')
            sizeratios_path = os.path.join(config.get_drawer_directory(drawer_id, 'fullsize'), 'sizeratios.csv')
            
            # Run the merge_data function with all available inputs
            merge_data(
                specimens_dir=specimens_dir,
                measurements_path=measurements_path if os.path.exists(measurements_path) else None,
                location_checked_path=location_checked_path if os.path.exists(location_checked_path) else None,
                taxonomy_path=taxonomy_path if os.path.exists(taxonomy_path) else None,
                unit_barcodes_path=unit_barcodes_path if os.path.exists(unit_barcodes_path) else None,
                geocodes_path=geocodes_path if os.path.exists(geocodes_path) else None,
                sizeratios_path=sizeratios_path if sizeratios_path and os.path.exists(sizeratios_path) else None,
                labels_dir=labels_dir if os.path.exists(labels_dir) else None,
                output_base_path=output_base_path
            )

def parse_arguments():
    all_steps = [
        'resize_drawers', 'find_color', 'crop_color', 'find_trays', 'crop_trays',
        'resize_trays', 'find_traylabels', 'crop_labels', 'find_specimens',
        'crop_specimens', 'create_traymaps', 'outline_specimens', 'create_masks',
        'fix_masks', 'measure_specimens', 'censor_background', 'outline_pins',
        'create_pinmask', 'create_transparency', 'transcribe_speclabels',
        'validate_speclabels', 'transcribe_barcodes', 'transcribe_geocodes', 'transcribe_taxonomy',
        'merge_data'
    ]
    
    parser = argparse.ArgumentParser(description="Process drawer images")
    parser.add_argument('steps', nargs='*', 
                    help='Steps to run')
    parser.add_argument('--from', dest='from_step', choices=all_steps, 
                    help='Run this step and all subsequent steps')
    parser.add_argument('--until', dest='until_step', choices=all_steps,
                    help='Run all steps up to and including this step')
    
    # Drawer selection options
    drawer_group = parser.add_argument_group('Drawer Selection')
    drawer_group.add_argument('--drawers', type=str,
                            help='Comma-separated list of drawer IDs to process (e.g., drawer_01,drawer_03)')
    drawer_group.add_argument('--list-drawers', action='store_true',
                            help='List available drawers and exit')
    drawer_group.add_argument('--status', action='store_true',
                            help='Show status report of all drawers and exit')
    drawer_group.add_argument('--write-report', action='store_true',
                            help='Write CSV status report to status_reports folder')

    # Processing options
    processing_group = parser.add_argument_group('Processing Options')
    processing_group.add_argument('--rerun', action='store_true',
                               help='Allow overwriting existing outputs (requires confirmation)')

    # Memory management options
    memory_group = parser.add_argument_group('Memory Management')
    sequential_group = memory_group.add_mutually_exclusive_group()
    sequential_group.add_argument('--sequential', action='store_true', dest='sequential',
                               help='Process images sequentially (one at a time)')
    sequential_group.add_argument('--parallel', action='store_false', dest='sequential',
                               help='Process images in parallel (default)')
    
    memory_group.add_argument('--max-workers', type=int, 
                            help='Maximum number of parallel workers')
    memory_group.add_argument('--batch-size', type=int,
                            help='Process images in batches of this size')
    
    # Set defaults to None to allow config to decide
    parser.set_defaults(sequential=None)
    
    # Model confidence and overlap parameters; overlap for object detection only
    model_group = parser.add_argument_group('Model Parameters')
    for model in ['drawer', 'tray', 'label', 'beetle', 'pin', 'color']:
        model_group.add_argument(f'--{model}_confidence', type=float,
                               help=f'Confidence threshold for {model} detection')
        if model not in ['beetle', 'pin']:
            model_group.add_argument(f'--{model}_overlap', type=float,
                                   help=f'Overlap threshold for {model} detection')
    
    return parser.parse_args()

def determine_steps(args, all_steps):
    valid_steps = all_steps + ['all']
    if args.steps:
        invalid_steps = [step for step in args.steps if step not in valid_steps]
        if invalid_steps:
            raise ValueError(f"Invalid steps: {', '.join(invalid_steps)}. Choose from: {', '.join(valid_steps)}")
    if not args.steps and (args.from_step or args.until_step):
        if args.from_step and args.until_step:
            start_idx = all_steps.index(args.from_step)
            end_idx = all_steps.index(args.until_step) + 1
            return all_steps[start_idx:end_idx]
        elif args.from_step:
            start_idx = all_steps.index(args.from_step)
            return all_steps[start_idx:]
        elif args.until_step:
            end_idx = all_steps.index(args.until_step) + 1
            return all_steps[:end_idx]
    elif args.steps:
        if 'all' in args.steps:
            if args.until_step:
                end_idx = all_steps.index(args.until_step) + 1
                return all_steps[:end_idx]
            elif args.from_step:
                start_idx = all_steps.index(args.from_step)
                return all_steps[start_idx:]
            return all_steps
        
        # For specified steps + from/until
        result = args.steps.copy()
        if args.from_step and args.until_step:
            start_idx = all_steps.index(args.from_step)
            end_idx = all_steps.index(args.until_step) + 1
            result.extend(all_steps[start_idx:end_idx])
        elif args.from_step:
            start_idx = all_steps.index(args.from_step)
            result.extend(all_steps[start_idx:])
        elif args.until_step:
            end_idx = all_steps.index(args.until_step) + 1
            result.extend(all_steps[:end_idx])
        return result
    else:
        raise ValueError("Please specify steps to run")

def confirm_rerun(steps_to_run, drawers_to_process):
    """
    Ask user to confirm before overwriting existing outputs.
    Returns True if user confirms, False otherwise.
    """
    print(f"\n{'='*60}")
    print("RERUN CONFIRMATION")
    print(f"{'='*60}")
    print(f"This will overwrite previous outputs of:")
    print(f"  Steps:   {', '.join(steps_to_run)}")
    print(f"  Drawers: {', '.join(drawers_to_process)}")
    print(f"{'='*60}")
    
    while True:
        response = input("Continue? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")

def clear_existing_outputs(config, drawer_id, steps_to_run):
    """
    Clear existing outputs for specified steps and drawer.
    Only removes outputs, not source directories.
    """
    # Define what outputs to clear for each step
    step_clear_mapping = {
        'resize_drawers': ['resized'],
        'find_color': ['color_coordinates'],
        'crop_color': ['colorstandard'],
        'find_trays': ['coordinates'], 
        'crop_trays': ['trays'],
        'resize_trays': ['resized_trays'],
        'find_traylabels': ['label_coordinates'],
        'crop_labels': ['labels'],
        'find_specimens': ['resized_trays_coordinates'],
        'crop_specimens': ['specimens'],
        'create_traymaps': ['guides'],
        'outline_specimens': ['mask_coordinates'],
        'create_masks': ['mask_png'],
        'fix_masks': [], # Don't clear, just re-process existing masks
        'measure_specimens': ['measurements'],
        'censor_background': ['no_background'],
        'outline_pins': ['pin_coordinates'],
        'create_pinmask': ['full_masks'],
        'create_transparency': ['transparencies', 'whitebg_specimens'],
        'transcribe_speclabels': ['specimen_level'],
        'validate_speclabels': [], # Don't clear, just re-process existing files
        'transcribe_barcodes': ['tray_level'],
        'transcribe_geocodes': [], # Don't clear tray_level if other transcription steps need it
        'transcribe_taxonomy': [], # Don't clear tray_level if other transcription steps need it  
        'merge_data': ['data']
    }
    
    cleared_dirs = []
    
    for step in steps_to_run:
        dirs_to_clear = step_clear_mapping.get(step, [])
        
        for dir_key in dirs_to_clear:
            try:
                output_path = config.get_drawer_directory(drawer_id, dir_key)
                if os.path.exists(output_path):
                    # Remove all contents but keep the directory
                    for item in os.listdir(output_path):
                        item_path = os.path.join(output_path, item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    cleared_dirs.append(f"{drawer_id}/{dir_key}")
            except Exception as e:
                log(f"Warning: Could not clear {drawer_id}/{dir_key}: {e}")
    
    if cleared_dirs:
        log(f"Cleared outputs from: {', '.join(cleared_dirs)}")

def generate_status_report(config, write_report=False):
    """
    Generate and display a status report showing what outputs exist for each drawer.
    Optionally write a CSV report to status_reports folder.
    """
    # Get all available drawers
    discover_and_sort_drawers(config)  # Sort any unsorted images first
    available_drawers = config.get_existing_drawers()
    
    if not available_drawers:
        log("No drawers found")
        return
    
    # Define the outputs to check for each step (removed fix_masks)
    step_outputs = {
        'resize_drawers': 'resized',
        'find_color': 'color_coordinates',
        'crop_color': 'colorstandard',
        'find_trays': 'coordinates', 
        'crop_trays': 'trays',
        'resize_trays': 'resized_trays',
        'find_traylabels': 'label_coordinates',
        'crop_labels': 'labels',
        'find_specimens': 'resized_trays_coordinates',
        'crop_specimens': 'specimens',
        'create_traymaps': 'guides',
        'outline_specimens': 'mask_coordinates',
        'create_masks': 'mask_png',
        'measure_specimens': 'measurements',
        'censor_background': 'no_background',
        'outline_pins': 'pin_coordinates',
        'create_pinmask': 'full_masks',
        'create_transparency': 'transparencies',
        'transcribe_speclabels': 'specimen_level',
        'validate_speclabels': 'specimen_level',
        'transcribe_barcodes': 'tray_level',
        'transcribe_geocodes': 'tray_level', 
        'transcribe_taxonomy': 'tray_level',
        'merge_data': 'data'
    }
    
    log("=" * 80)
    log("DRAWER STATUS REPORT")
    log("=" * 80)
    
    # Data for CSV report
    report_data = []
    
    for drawer_id in available_drawers:
        drawer_type = "specimen-only" if is_specimen_only_drawer(config, drawer_id) else "standard"
        log(f"\n{drawer_id} ({drawer_type}):")
        log("-" * 40)
        
        outputs_found = []
        outputs_missing = []
        
        # Dictionary to store status for CSV report
        drawer_status = {'drawer_id': drawer_id}
        
        for step, output_dir in step_outputs.items():
            try:
                output_path = config.get_drawer_directory(drawer_id, output_dir)
                
                # Check if directory exists and has content
                has_output = False
                if os.path.exists(output_path):
                    if step == 'measure_specimens':
                        # Check for measurements.csv specifically
                        has_output = os.path.exists(os.path.join(output_path, 'measurements.csv'))
                    elif step == 'transcribe_speclabels':
                        # Check for location_frags.csv in specimen_level
                        has_output = os.path.exists(os.path.join(output_path, 'location_frags.csv'))
                    elif step == 'validate_speclabels':
                        # Check for location_checked.csv in specimen_level
                        has_output = os.path.exists(os.path.join(output_path, 'location_checked.csv'))
                    elif step == 'transcribe_barcodes':
                        # Check for unit_barcodes.csv in tray_level
                        has_output = os.path.exists(os.path.join(output_path, 'unit_barcodes.csv'))
                    elif step == 'transcribe_geocodes':
                        # Check for geocodes.csv in tray_level
                        has_output = os.path.exists(os.path.join(output_path, 'geocodes.csv'))
                    elif step == 'transcribe_taxonomy':
                        # Check for taxonomy.csv in tray_level
                        has_output = os.path.exists(os.path.join(output_path, 'taxonomy.csv'))
                    elif step == 'merge_data':
                        # Check for any timestamped folders and get most recent
                        timestamped_dirs = [item for item in os.listdir(output_path) 
                                          if os.path.isdir(os.path.join(output_path, item))]
                        has_output = len(timestamped_dirs) > 0
                        if has_output:
                            # Find most recent timestamp
                            most_recent = max(timestamped_dirs)
                            drawer_status['merge_data_timestamp'] = most_recent
                    elif step in ['crop_specimens', 'outline_specimens', 'create_masks', 'censor_background', 
                                'outline_pins', 'create_pinmask', 'create_transparency']:
                        # These steps create tray-specific subfolders, check for any subfolder with files
                        has_output = False
                        try:
                            # Look for any subdirectories (tray folders)
                            subdirs = [item for item in os.listdir(output_path) 
                                     if os.path.isdir(os.path.join(output_path, item))]
                            for subdir in subdirs:
                                subdir_path = os.path.join(output_path, subdir)
                                # Check if this tray folder has any files
                                if any(os.path.isfile(os.path.join(subdir_path, f)) 
                                      for f in os.listdir(subdir_path)):
                                    has_output = True
                                    break
                        except (OSError, PermissionError):
                            has_output = False
                    else:
                        # Check for any files in the directory (for non-nested steps)
                        has_output = any(os.path.isfile(os.path.join(output_path, f)) for f in os.listdir(output_path))
                
                if has_output:
                    outputs_found.append(step)
                    drawer_status[step] = 'complete'
                else:
                    outputs_missing.append(step)
                    drawer_status[step] = 'missing'
                    
            except Exception:
                outputs_missing.append(step)
                drawer_status[step] = 'missing'
        
        # Display results
        if outputs_found:
            log(f"  ✓ Completed: {', '.join(outputs_found)}")
        if outputs_missing:
            log(f"  ✗ Missing:   {', '.join(outputs_missing)}")
        
        # Special display for merge_data timestamp
        if 'merge_data_timestamp' in drawer_status:
            log(f" Most recent merge: {drawer_status['merge_data_timestamp']}")
        
        if not outputs_found and not outputs_missing:
            log("  (No outputs detected)")
        
        # Add to report data
        report_data.append(drawer_status)
    
    log("\n" + "=" * 80)
    
    # Write CSV report if requested
    if write_report:
        write_status_csv_report(config, report_data, step_outputs.keys())

def write_status_csv_report(config, report_data, step_names):
    """
    Write a timestamped CSV report to the status_reports folder.
    """
    # Create status_reports directory in the same directory as process_images.py
    script_dir = os.path.dirname(os.path.abspath(__file__))
    status_reports_dir = os.path.join(script_dir, 'status_reports')
    os.makedirs(status_reports_dir, exist_ok=True)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"report_{timestamp}.csv"
    report_path = os.path.join(status_reports_dir, report_filename)
    
    # Get Roboflow model info from config
    model_info = {}
    if hasattr(config, 'roboflow_models'):
        for model_name, model_config in config.roboflow_models.items():
            model_info[f'{model_name}_endpoint'] = model_config.get('endpoint', 'N/A')
            model_info[f'{model_name}_version'] = model_config.get('version', 'N/A')
    
    # Prepare CSV headers
    headers = ['drawer_id'] + list(step_names) + ['merge_data_timestamp'] + list(model_info.keys())
    
    # Write CSV
    with open(report_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for drawer_data in report_data:
            # Merge drawer data with model info
            row_data = {**drawer_data, **model_info}
            # Fill missing values with empty strings
            for header in headers:
                if header not in row_data:
                    row_data[header] = ''
            writer.writerow(row_data)
    
    log(f"CSV report written to: {report_path}")

# Main Function
def main():
    start_time = time.time()
    
    config = DrawerDissectConfig()
    
    all_steps = [
        'resize_drawers', 'find_color', 'crop_color', 'find_trays', 'crop_trays',
        'resize_trays', 'find_traylabels', 'crop_labels', 'find_specimens',
        'crop_specimens', 'create_traymaps', 'outline_specimens', 'create_masks',
        'fix_masks', 'measure_specimens', 'censor_background', 'outline_pins',
        'create_pinmask', 'create_transparency', 'transcribe_speclabels',
        'validate_speclabels', 'transcribe_barcodes', 'transcribe_geocodes', 
        'transcribe_taxonomy', 'merge_data'
    ]
    
    # Define steps that are valid for specimen-only drawers
    specimen_only_steps = [
        'outline_specimens', 'create_masks', 'fix_masks', 'measure_specimens',
        'censor_background', 'outline_pins', 'create_pinmask', 'create_transparency',
        'transcribe_speclabels', 'validate_speclabels', 'merge_data'
    ]
    
    try:
        args = parse_arguments()
        
        # Handle status report
        if args.status:
            generate_status_report(config, write_report=args.write_report)
            return
        
        if args.list_drawers:
            discover_and_sort_drawers(config)  # Sort any unsorted images first
            available = config.get_existing_drawers()
            if available:
                log("Available drawers:")
                for drawer in available:
                    drawer_type = "specimen-only" if is_specimen_only_drawer(config, drawer) else "standard"
                    log(f"  - {drawer} ({drawer_type})")
            else:
                log("No drawers found")
            return
        
        # Parse drawer selection
        specified_drawers = None
        if args.drawers:
            specified_drawers = [d.strip() for d in args.drawers.split(',')]
        
        # Get drawers to process
        drawers_to_process = get_drawers_to_process(config, specified_drawers)
        if not drawers_to_process:
            log("No drawers to process")
            return
        
        # Validate drawer structures and categorize
        valid_drawers = []
        specimen_only_drawers = []
        
        for drawer_id in drawers_to_process:
            if validate_drawer_structure(config, drawer_id):
                valid_drawers.append(drawer_id)
                if is_specimen_only_drawer(config, drawer_id):
                    specimen_only_drawers.append(drawer_id)
            else:
                log(f"Skipping invalid drawer: {drawer_id}")
        
        if not valid_drawers:
            log("No valid drawers to process")
            return
        
        steps_to_run = determine_steps(args, all_steps)
        
        # Handle rerun confirmation
        if args.rerun:
            if not confirm_rerun(steps_to_run, valid_drawers):
                log("Operation cancelled by user")
                return
            
            # Clear existing outputs for all selected drawers and steps
            log("Clearing existing outputs...")
            for drawer_id in valid_drawers:
                clear_existing_outputs(config, drawer_id, steps_to_run)
        
        # Filter steps for specimen-only drawers
        if specimen_only_drawers:
            invalid_steps_for_specimens = [step for step in steps_to_run 
                                         if step not in specimen_only_steps]
            if invalid_steps_for_specimens:
                log(f"Warning: Steps {invalid_steps_for_specimens} not supported for specimen-only drawers")
                log(f"Specimen-only drawers ({specimen_only_drawers}) will skip these steps")
        
    except ValueError as e:
        log(f"Error: {e}")
        return

    # Log startup information
    log("DrawerDissect Pipeline")
    log("=====================")
    log(f"Processing drawers: {', '.join(valid_drawers)}")
    if specimen_only_drawers:
        log(f"Specimen-only drawers: {', '.join(specimen_only_drawers)}")
    log(f"Running steps: {', '.join(steps_to_run)}")
    if args.rerun:
        log("Mode: RERUN (overwriting existing outputs)")
    
    # Initialize Roboflow if needed
    rf_instance = workspace_instance = None
    roboflow_steps = {'find_color','find_trays', 'find_traylabels', 'find_specimens', 
                    'outline_specimens', 'outline_pins'}
    if set(steps_to_run) & roboflow_steps:
        rf_instance, workspace_instance = get_roboflow_instance(config)
    
    # Process each drawer
    for drawer_id in valid_drawers:
        log(f"\n{'='*20} Processing {drawer_id} {'='*20}")
        
        # Determine which steps to run for this drawer
        is_specimen_only = drawer_id in specimen_only_drawers
        drawer_steps = []
        
        for step in steps_to_run:
            if is_specimen_only and step not in specimen_only_steps:
                log(f"Skipping {step} for specimen-only drawer {drawer_id}")
                continue
            drawer_steps.append(step)
        
        if not drawer_steps:
            log(f"No valid steps to run for drawer {drawer_id}")
            continue
        
        for step in drawer_steps:
            log(f"Running {step} for {drawer_id}")
            run_step_for_drawer(step, config, drawer_id, args, rf_instance, workspace_instance)

    # Final timing report
    total_time = time.time() - start_time
    hours = int(total_time // 3600)
    minutes = int((total_time % 3600) // 60)
    seconds = total_time % 60
    
    if hours > 0:
        time_str = f"{hours}h {minutes}m {seconds:.2f}s"
    elif minutes > 0:
        time_str = f"{minutes}m {seconds:.2f}s"
    else:
        time_str = f"{seconds:.2f}s"
        
    log("\n" + "=" * 50)
    log(f"Pipeline completed successfully")
    log(f"Total processing time: {time_str}")
    log("=" * 50)

if __name__ == '__main__':
    main()
