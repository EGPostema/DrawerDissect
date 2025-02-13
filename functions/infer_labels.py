import os
import json
import tempfile
import logging
from PIL import Image
from contextlib import contextmanager
from roboflow import Roboflow

# Configure logging to reduce verbosity
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('roboflow').setLevel(logging.WARNING)
logging.getLogger('PIL').setLevel(logging.INFO)

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
    os.makedirs(output_dir, exist_ok=True)
    project = rf_instance.workspace().project(model_endpoint)
    model = project.version(version).model
    
    processed = errors = 0

    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('_1000.jpg'):
                continue

            json_path = os.path.join(output_dir, file.replace('_1000.jpg', '_1000_label.json'))
            if os.path.exists(json_path):
                continue  # Skip silently

            file_path = os.path.join(root, file)
            try:
                with temporary_jpg_if_needed(file_path) as inference_path:
                    prediction = model.predict(inference_path, confidence=confidence, overlap=overlap).json()
                with open(json_path, 'w') as json_file:
                    json.dump(prediction, json_file)
                processed += 1
                print(f"Processed: {file}")
            except Exception as e:
                errors += 1
                print(f"Error: {file} - {str(e)}")

    print(f"Complete. Processed: {processed}, Errors: {errors}")