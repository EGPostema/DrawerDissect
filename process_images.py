# Imports
import os
import time
import argparse
import roboflow
import asyncio
from functools import lru_cache
from typing import Tuple, Dict, Any
from config import DrawerDissectConfig
from logging_utils import log, StepTimer
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

# Defining steps
def run_step(step, config, args, rf_instance=None, workspace_instance=None):
    """Run a specific pipeline step with appropriate configuration."""
    with StepTimer(step):
        # Get memory management settings for this step from config - STILL NEED TO INTEGRATE BETTER
        mem_config = config.get_memory_config(step)
        
        # Command-line args override config settings
        sequential = args.sequential if args.sequential is not None else mem_config.get('sequential', False)
        max_workers = args.max_workers if args.max_workers is not None else mem_config.get('max_workers')
        batch_size = args.batch_size if args.batch_size is not None else mem_config.get('batch_size')
        
        # Log memory management settings if they're non-default
        if sequential or max_workers is not None or batch_size is not None:
            log(f"Memory settings: sequential={sequential}, max_workers={max_workers}, batch_size={batch_size}")
        
        if step in {'find_trays', 'find_traylabels', 'find_specimens', 
                    'outline_specimens', 'outline_pins'} and not rf_instance:
                rf_instance, workspace_instance = get_roboflow_instance(config)
                
        if step == 'resize_drawers':
            resize_drawer_images(
                config.directories['fullsize'], 
                config.directories['resized'],
                sequential=sequential,
                max_workers=max_workers,
                batch_size=batch_size
            )
        
        elif step == 'process_metadata':
            if config.processing_flags['process_metadata']:
                process_files(
                    config.directories['metadata'],
                    config.directories['fullsize'],
                    os.path.join(config.directories['metadata'], 'sizeratios.csv')
                )
            else:
                log("Metadata processing disabled in config - skipping")
        
        elif step == 'find_trays':
            drawer_model = config.roboflow_models['drawer']
            infer_drawers(
                config.directories['resized'],
                config.directories['coordinates'],
                rf_instance,
                workspace_instance,
                drawer_model['endpoint'],
                drawer_model['version'],
                confidence=args.drawer_confidence or drawer_model['confidence'],
                overlap=args.drawer_overlap or drawer_model['overlap']
            )
        
        elif step == 'crop_trays':
            crop_trays_from_fullsize(
                config.directories['fullsize'],
                config.directories['resized'],
                config.directories['trays'],
                sequential=sequential,
                max_workers=max_workers,
                batch_size=batch_size
            )
        
        elif step == 'resize_trays':
            resize_tray_images(
                config.directories['trays'],
                config.directories['resized_trays']
            )
        
        elif step == 'find_traylabels':
            label_model = config.roboflow_models['label']
            infer_tray_labels(
                config.directories['resized_trays'],
                config.directories['label_coordinates'],
                rf_instance,
                workspace_instance,
                label_model['endpoint'],
                label_model['version'],
                confidence=args.label_confidence or label_model['confidence'],
                overlap=args.label_overlap or label_model['overlap']
            )
        
        elif step == 'crop_labels':
            crop_labels(
                config.directories['trays'],
                config.directories['resized_trays'],
                config.directories['label_coordinates'],
                config.directories['labels']
            )
        
        elif step == 'find_specimens':
            tray_model = config.roboflow_models['tray']
            infer_tray_images(
                config.directories['resized_trays'],
                config.directories['resized_trays_coordinates'],
                rf_instance,
                workspace_instance,
                tray_model['endpoint'],
                tray_model['version'],
                confidence=args.tray_confidence or tray_model['confidence'],
                overlap=args.tray_overlap or tray_model['overlap']
            )
        
        elif step == 'crop_specimens':
            crop_specimens_from_trays(
                config.directories['trays'],
                config.directories['resized_trays'],
                config.directories['specimens']
            )
        
        elif step == 'create_traymaps':
            create_specimen_guides(
                config.directories['resized_trays'],
                config.directories['guides']
            )
        
        elif step == 'outline_specimens':
            mask_model = config.roboflow_models['mask']
            infer_beetles(
                config.directories['specimens'],
                config.directories['mask_coordinates'],
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
                config.directories['mask_coordinates'],
                config.directories['mask_png']
            )
        
        elif step == 'fix_masks':
            fix_mask(config.directories['mask_png'])
        
        elif step == 'measure_specimens':
            metadata_file = None
            if config.processing_flags['process_metadata']:
                metadata_file = os.path.join(config.directories['metadata'], 'sizeratios.csv')
            
            generate_csv_with_measurements(
                config.directories['mask_png'],
                metadata_file,
                config.directories['measurements']
            )
        
        elif step == 'censor_background':
            censor_background(
                config.directories['specimens'],
                config.directories['mask_png'],
                config.directories['no_background']
            )
        
        elif step == 'outline_pins':
            pin_model = config.roboflow_models['pin']
            infer_pins(
                config.directories['no_background'],
                config.directories['pin_coordinates'],
                os.path.join(config.directories['measurements'], 'measurements.csv'),
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
                config.directories['mask_png'],
                config.directories['pin_coordinates'],
                config.directories['full_masks']
            )
        
        elif step == 'create_transparency':
            create_transparency(
                config.directories['no_background'],
                config.directories['full_masks'],
                config.directories['transparencies'],
                config.directories['whitebg_specimens'],
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
                    config.directories['specimens'],
                    os.path.join(config.directories['specimen_level'], 'location_frags.csv'),
                    config.api_keys['anthropic'],
                    prompts=prompts
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
                    os.path.join(config.directories['specimen_level'], 'location_frags.csv'),
                    os.path.join(config.directories['specimen_level'], 'location_checked.csv'),
                    config.api_keys['anthropic'],
                    prompts=prompts
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
                    config.directories['labels'],
                    os.path.join(config.directories['tray_level'], 'unit_barcodes.csv'),
                    config.api_keys['anthropic'],
                    prompts=prompts
                ))
            else:
                log("Barcode transcription disabled in config - skipping")

        elif step == 'transcribe_taxonomy':
            if config.processing_flags['transcribe_taxonomy']:
                prompts = {
                    'system': config.prompts['taxonomy']['system'],
                    'user': config.prompts['taxonomy']['user']
                }
                asyncio.run(process_image_folder(
                    config.directories['labels'],
                    os.path.join(config.directories['tray_level'], 'taxonomy.csv'),
                    config.api_keys['anthropic'],
                    prompts=prompts
                ))
            else:
                log("Taxonomy transcription disabled in config - skipping")
        
        elif step == 'merge_data':
            output_base_path = os.path.join(config.directories['data'], 'merged_data')
            merge_data(
                os.path.join(config.directories['measurements'], 'measurements.csv'),
                os.path.join(config.directories['specimen_level'], 'location_checked.csv'),
                os.path.join(config.directories['tray_level'], 'taxonomy.csv'),
                os.path.join(config.directories['tray_level'], 'unit_barcodes.csv'),
                output_base_path,
                mode="FMNH" if config.processing_flags['process_metadata'] else "Default",
            )

# Ordering steps, adding --from and --until
def parse_arguments():
    all_steps = [
        'resize_drawers', 'process_metadata', 'find_trays', 'crop_trays',
        'resize_trays', 'find_traylabels', 'crop_labels', 'find_specimens',
        'crop_specimens', 'create_traymaps', 'outline_specimens', 'create_masks',
        'fix_masks', 'measure_specimens', 'censor_background', 'outline_pins',
        'create_pinmask', 'create_transparency', 'transcribe_speclabels',
        'validate_speclabels', 'transcribe_barcodes', 'transcribe_taxonomy',
        'merge_data'
    ]
    
    parser = argparse.ArgumentParser(description="Process drawer images")
    parser.add_argument('steps', nargs='*', choices=all_steps + ['all'], 
                      help='Steps to run')
    parser.add_argument('--from', dest='from_step', choices=all_steps, 
                      help='Run this step and all subsequent steps')
    parser.add_argument('--until', dest='until_step', choices=all_steps,
                      help='Run all steps up to and including this step')
    
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
    
    # Model confidence and overlap parameters
    model_group = parser.add_argument_group('Model Parameters')
    for model in ['drawer', 'tray', 'label', 'beetle', 'pin']:
        model_group.add_argument(f'--{model}_confidence', type=float,
                               help=f'Confidence threshold for {model} detection')
        if model not in ['beetle', 'pin']:
            model_group.add_argument(f'--{model}_overlap', type=float,
                                   help=f'Overlap threshold for {model} detection')
    
    return parser.parse_args()

# Allowing steps to be called individually, in combinations, etc
def determine_steps(args, all_steps):
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
            return all_steps
        return args.steps
    else:
        raise ValueError("Please specify steps to run")

# Main Function
def main():
    start_time = time.time()
    
    config = DrawerDissectConfig()
    
    all_steps = [
        'resize_drawers', 'process_metadata', 'find_trays', 'crop_trays',
        'resize_trays', 'find_traylabels', 'crop_labels', 'find_specimens',
        'crop_specimens', 'create_traymaps', 'outline_specimens', 'create_masks',
        'fix_masks', 'measure_specimens', 'censor_background', 'outline_pins',
        'create_pinmask', 'create_transparency', 'transcribe_speclabels',
        'validate_speclabels', 'transcribe_barcodes', 'transcribe_taxonomy',
        'merge_data'
    ]
    
    try:
        args = parse_arguments()
        steps_to_run = determine_steps(args, all_steps)
    except ValueError as e:
        log(f"Error: {e}")
        return

    # Log startup information - STILL NEED TO INTEGRATE BETTER
    log("DrawerDissect Pipeline")
    log("=====================")
    log(f"Running steps: {', '.join(steps_to_run)}")
    
    rf_instance = workspace_instance = None
    roboflow_steps = {'find_trays', 'find_traylabels', 'find_specimens', 
                    'outline_specimens', 'outline_pins'}
    if set(steps_to_run) & roboflow_steps:
        rf_instance, workspace_instance = get_roboflow_instance(config)
    
    for step in steps_to_run:
        log(f"\nRunning step: {step}")
        run_step(step, config, args, rf_instance, workspace_instance)

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
