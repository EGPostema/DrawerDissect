import os
import json
import tempfile
import pandas as pd
import logging
from PIL import Image
from contextlib import contextmanager
from roboflow import Roboflow

# Configure logging
logging.getLogger('PIL').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.WARNING)  # Silence urllib3 debug messages
logging.getLogger('roboflow').setLevel(logging.WARNING)  # Silence Roboflow debug messages if any

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

def infer_pins(input_dir, output_dir, csv_path, rf_instance, workspace_instance, model_endpoint, version, confidence=50):
    # Load and filter the CSV data
    data = pd.read_csv(csv_path)
    filtered_data = data[data['mask_OK'] == 'Y']
    valid_ids = set(filtered_data['full_id'])
    
    # Initialize the Roboflow project and model
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    
    # Define valid extensions
    valid_extensions = ('.tif', '.tiff', '.png', '.jpg', '.jpeg')
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            # Check for valid extensions and '_masked' in the filename
            if not file.lower().endswith(valid_extensions) or '_masked' not in file:
                continue
            
            # Extract full_id by removing '_masked' and the file extension
            full_id = file.replace('_masked', '').rsplit('.', 1)[0]
            
            # Skip files not in valid_ids
            if full_id not in valid_ids:
                continue
                
            # Create output subfolder
            relative_path = os.path.relpath(root, input_dir)
            output_subfolder = os.path.join(output_dir, relative_path)
            os.makedirs(output_subfolder, exist_ok=True)
            
            # Define the JSON filename and path
            json_filename = file.rsplit('.', 1)[0] + '.json'
            json_path = os.path.join(output_subfolder, json_filename)
            
            # Skip if the JSON file already exists
            if os.path.exists(json_path):
                continue  # Removed the print statement for existing files
                
            file_path = os.path.join(root, file)
            
            try:
                # Handle temporary conversion for TIFFs if needed
                with temporary_jpg_if_needed(file_path) as inference_path:
                    # Run inference
                    prediction = model.predict(inference_path, confidence=confidence).json()
                
                # Save predictions to a JSON file
                with open(json_path, 'w') as json_file:
                    json.dump(prediction, json_file)
                print(f"Processed {file}")  # Simplified progress message
            except Exception as e:
                print(f"Error processing {file}: {e}")



