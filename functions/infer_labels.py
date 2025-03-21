import os
import json
import tempfile
from PIL import Image
from contextlib import contextmanager
from logging_utils import log, log_found, log_progress

@contextmanager
def temporary_jpg_if_needed(image_path):
    """Creates temporary JPG version if image is TIFF."""
    if image_path.lower().endswith(('.jpg', '.jpeg', '.png')):
        yield image_path
    else:  # Handle TIFFs
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=True) as tmp:
            with Image.open(image_path) as img:
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    img = img.convert('RGB')
                img.save(tmp.name, 'JPEG', quality=95)
            yield tmp.name

def infer_tray_labels(input_dir, output_dir, rf_instance, workspace_instance, model_endpoint, version, confidence=50, overlap=50):
    """
    Detect label components in tray images using the Roboflow model.
    
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
    
    # Initialize model
    log(f"Using model: {model_endpoint} v{version} (confidence: {confidence}, overlap: {overlap})")
    project = rf_instance.workspace().project(model_endpoint)
    model = project.version(version).model
    
    # Find all resized tray image files
    image_files = [f for f in os.listdir(input_dir) if f.endswith('_1000.jpg')]
    total_files = len(image_files)
    
    if not total_files:
        log("No resized tray images found to process")
        return
        
    log_found("images", total_files)
    
    # Track existing files that can be skipped
    existing_files = [f.replace('_1000_label.json', '_1000.jpg') 
                      for f in os.listdir(output_dir) 
                      if f.endswith('_1000_label.json')]
    
    if existing_files:
        log(f"Found {len(existing_files)} previously processed images")
    
    # Process images
    processed = 0
    skipped = 0
    errors = 0

    for i, file in enumerate(image_files, 1):
        json_path = os.path.join(output_dir, file.replace('_1000.jpg', '_1000_label.json'))
        
        # Skip if already processed
        if file in existing_files:
            log_progress("find_traylabels", i, total_files, f"Skipped (already exists)")
            skipped += 1
            continue

        file_path = os.path.join(input_dir, file)
        
        try:
            with temporary_jpg_if_needed(file_path) as inference_path:
                prediction = model.predict(inference_path, confidence=confidence, overlap=overlap).json()
                
            with open(json_path, 'w') as json_file:
                json.dump(prediction, json_file)
                
            label_count = len(prediction.get('predictions', []))
            log_progress("find_traylabels", i, total_files, f"Found {label_count} label components")
            processed += 1
            
        except Exception as e:
            log(f"Error processing {file}: {str(e)}")
            errors += 1

    log(f"Complete. {processed} processed, {skipped} skipped, {errors} errors")