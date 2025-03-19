import os
import json
import tempfile
import logging
from PIL import Image
from contextlib import contextmanager
from typing import Optional
from roboflow import Roboflow

# Configure logging to reduce verbosity
logging.getLogger('PIL').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('roboflow').setLevel(logging.WARNING)

@contextmanager
def temporary_jpg_if_needed(image_path):
    """Creates temporary JPG version if image is TIFF."""
    if image_path.lower().endswith(('.jpg', '.jpeg', '.png')):
        yield image_path
    else:  # Handle TIFFs
        temp_dir = os.path.dirname(image_path)  # Use the same directory as the original file
        with tempfile.NamedTemporaryFile(suffix='.jpg', dir=temp_dir, delete=False) as tmp:
            temp_file_path = tmp.name
        try:
            with Image.open(image_path) as img:
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    img = img.convert('RGB')
                img.save(temp_file_path, 'JPEG', quality=95)
            yield temp_file_path
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

def infer_beetles(
    input_dir: str,
    output_dir: str,
    rf_instance: Roboflow,
    workspace_instance,
    model_endpoint: str,
    version: int,
    confidence: Optional[float] = 50
):
    """
    Args:
        input_dir: Directory containing specimen images
        output_dir: Directory to save JSON outputs
        rf_instance: Roboflow instance
        workspace_instance: Workspace instance from Roboflow
        model_endpoint: Name of the model
        version: Version number of the model
        confidence: Confidence threshold (0-100)
    """
    # Initialize model
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    processed = errors = 0
    
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    
    # Walk through the input directory
    for root, _, files in os.walk(input_dir):
        # Filter for image files
        image_files = [f for f in files if f.lower().endswith(supported_formats)]
        if not image_files:
            continue
            
        # Extract path information
        relative_path = os.path.relpath(root, input_dir)
        path_parts = relative_path.split(os.sep)
        
        if len(path_parts) < 2:
            continue  # Skip invalid folder structures
            
        # Create output subfolder
        drawer_id, tray_number = path_parts[:2]
        output_subfolder = os.path.join(output_dir, drawer_id, tray_number)
        os.makedirs(output_subfolder, exist_ok=True)
        
        # Process each image
        for file in image_files:
            # Define output JSON path
            json_path = os.path.join(output_subfolder, os.path.splitext(file)[0] + '.json')
            
            # Skip if already processed
            if os.path.exists(json_path):
                continue
                
            try:
                # Run inference with temporary conversion if needed
                file_path = os.path.join(root, file)
                with temporary_jpg_if_needed(file_path) as inference_path:
                    prediction = model.predict(inference_path, confidence=confidence).json()
                
                # Save results
                with open(json_path, 'w') as f:
                    json.dump(prediction, f, indent=2)
                
                processed += 1
                print(f"Processed: {file}")
                
            except Exception as e:
                errors += 1
                print(f"Error: {file} - {str(e)}")
                continue

    print(f"Complete. Processed: {processed}, Errors: {errors}")







