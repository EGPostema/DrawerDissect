import os
import json
from roboflow import Roboflow
from logging_utils import log, log_found, log_progress

def infer_drawers(input_dir, output_dir, rf_instance, workspace_instance, model_endpoint, version, confidence=50, overlap=50):
    """
    Detect trays in drawer images using the Roboflow model.
    
    Args:
        input_dir: Directory containing resized drawer images
        output_dir: Directory to save prediction coordinates
        rf_instance: Roboflow API instance
        workspace_instance: Roboflow workspace instance 
        model_endpoint: Name of model to use
        version: Model version
        confidence: Detection confidence threshold (0-100)
        overlap: Object overlap threshold (0-100)
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize model
    log(f"Using model: {model_endpoint} v{version} (confidence: {confidence}, overlap: {overlap})")
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    
    # Safely remove resize preprocessing if it exists
    if hasattr(model, 'preprocessing') and 'resize' in model.preprocessing:
        del model.preprocessing['resize']
    
    # Find all drawer image files
    image_files = []
    for root, _, files in os.walk(input_dir):
        for f in files:
            if f.endswith('_1000.jpg'):
                image_files.append(os.path.join(root, f))
    total_files = len(image_files)
    log_found("images", total_files)
    
    # Track processing stats
    processed = 0
    skipped = 0
    
    # Process each file
    for i, file_path in enumerate(image_files, 1):
        filename = os.path.basename(file_path)
        json_path = os.path.join(output_dir, filename.replace('.jpg', '.json'))
        
        # Check if JSON file already exists
        if os.path.exists(json_path):
            log_progress("find_trays", i, total_files, f"Skipped (already exists)")
            skipped += 1
            continue
            
        try:
            # Run inference using full file_path
            raw_prediction = model.predict(file_path, confidence=confidence, overlap=overlap)
            prediction = raw_prediction.json()
            
            # Save prediction results
            with open(json_path, 'w') as json_file:
                json.dump(prediction, json_file)
            
            # Log progress
            tray_count = len(prediction.get('predictions', []))
            log_progress("find_trays", i, total_files, f"Found {tray_count} trays")
            processed += 1
            
        except Exception as e:
            log(f"Error processing {file}: {str(e)}")









