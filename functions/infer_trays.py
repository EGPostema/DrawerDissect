import os
import json
from logging_utils import log, log_found, log_progress

def infer_tray_images(input_dir, output_dir, rf_instance, workspace_instance, model_endpoint, version, confidence=50, overlap=50):
    """
    Detect specimens in tray images using the Roboflow model.
    
    Args:
        input_dir: Directory containing resized tray images
        output_dir: Directory to save prediction coordinates
        rf_instance: Roboflow API instance
        workspace_instance: Roboflow workspace instance 
        model_endpoint: Name of model to use
        version: Model version
        confidence: Detection confidence threshold (0-100)
        overlap: Object overlap threshold (0-100)
    """
    os.makedirs(output_dir, exist_ok=True)

    # Get model from workspace
    log(f"Using model: {model_endpoint} v{version} (confidence: {confidence}, overlap: {overlap})")
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    
    # Find all resized tray images - RECURSIVELY SEARCH SUBDIRECTORIES
    image_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('_1000.jpg'):
                # Store the full path and the file name
                image_files.append((os.path.join(root, file), file))
    
    total_files = len(image_files)
    
    if not total_files:
        log("No resized tray images found to process")
        return
        
    log_found("images", total_files)
    
    # Track existing files that can be skipped
    existing_files = [f.replace('_1000.json', '_1000.jpg') 
                    for f in os.listdir(output_dir) 
                    if f.endswith('_1000.json')]
    
    if existing_files:
        log(f"Found {len(existing_files)} previously processed images")
    
    # Track results
    processed = 0
    skipped = 0
    errors = 0

    for i, (file_path, file_name) in enumerate(image_files, 1):
        # Create mirrored directory structure in output
        relative_path = os.path.relpath(os.path.dirname(file_path), input_dir)
        if relative_path != '.':  # If file is in a subdirectory
            output_subdir = os.path.join(output_dir, relative_path)
            os.makedirs(output_subdir, exist_ok=True)
            json_path = os.path.join(output_subdir, file_name.replace('_1000.jpg', '_1000.json'))
        else:  # If file is in the top-level directory
            json_path = os.path.join(output_dir, file_name.replace('_1000.jpg', '_1000.json'))
        
        # Skip if already processed - check using file name only
        if file_name in existing_files:
            log_progress("find_specimens", i, total_files, f"Skipped (already exists)")
            skipped += 1
            continue
        
        try:
            prediction = model.predict(file_path, confidence=confidence, overlap=overlap).json()
            
            with open(json_path, 'w') as json_file:
                json.dump(prediction, json_file)
                
            specimen_count = len(prediction.get('predictions', []))
            log_progress("find_specimens", i, total_files, f"Found {specimen_count} specimens")
            processed += 1
            
        except Exception as e:
            log(f"Error processing {file_name}: {str(e)}")
            errors += 1
    
    log(f"Complete. {processed} processed, {skipped} skipped, {errors} errors")

