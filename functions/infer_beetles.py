import os
import json
import tempfile
import logging
import pandas as pd
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
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    processed = errors = 0
    
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    
    for root, _, files in os.walk(input_dir):
        image_files = [f for f in files if f.lower().endswith(supported_formats)]
        if not image_files:
            continue
            
        relative_path = os.path.relpath(root, input_dir)
        path_parts = relative_path.split(os.sep)
        
        if len(path_parts) < 2:
            continue  # Silently skip invalid folder structures
            
        drawer_id, tray_number = path_parts[:2]
        output_subfolder = os.path.join(output_dir, drawer_id, tray_number)
        os.makedirs(output_subfolder, exist_ok=True)
        
        for file in image_files:
            json_path = os.path.join(output_subfolder, os.path.splitext(file)[0] + '.json')
            
            if os.path.exists(json_path):
                continue  # Skip silently
                
            try:
                file_path = os.path.join(root, file)
                with temporary_jpg_if_needed(file_path) as inference_path:
                    prediction = model.predict(inference_path, confidence=confidence).json()
                
                with open(json_path, 'w') as f:
                    json.dump(prediction, f, indent=2)
                
                processed += 1
                print(f"Processed: {file}")
                
            except Exception as e:
                errors += 1
                print(f"Error: {file} - {str(e)}")
                continue

    print(f"Complete. Processed: {processed}, Errors: {errors}")

def infer_pins(input_dir, output_dir, csv_path, rf_instance, workspace_instance, model_endpoint, version, confidence=50):
    data = pd.read_csv(csv_path)
    filtered_data = data[data['mask_OK'] == 'Y']
    valid_ids = set(filtered_data['full_id'])
    
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    processed = errors = 0
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('_masked.png'):
                continue
                
            full_id = file.replace('_masked.png', '')
            if full_id not in valid_ids:
                continue
                
            relative_path = os.path.relpath(root, input_dir)
            output_subfolder = os.path.join(output_dir, relative_path)
            os.makedirs(output_subfolder, exist_ok=True)
            
            json_filename = file.replace('.png', '.json')
            json_path = os.path.join(output_subfolder, json_filename)
            
            if os.path.exists(json_path):
                continue  # Skip silently
                
            file_path = os.path.join(root, file)
            
            try:
                with temporary_jpg_if_needed(file_path) as inference_path:
                    prediction = model.predict(inference_path, confidence=confidence).json()
                
                with open(json_path, 'w') as json_file:
                    json.dump(prediction, json_file)
                processed += 1
                print(f"Processed: {file}")
            except Exception as e:
                errors += 1
                print(f"Error: {file} - {str(e)}")
    
    print(f"Complete. Processed: {processed}, Errors: {errors}")







