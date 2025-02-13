import os
import json
import logging
from roboflow import Roboflow

# Configure logging to reduce verbosity
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('roboflow').setLevel(logging.WARNING)

def infer_tray_images(input_dir, output_dir, rf_instance, workspace_instance, model_endpoint, version, confidence=50, overlap=50):
    os.makedirs(output_dir, exist_ok=True)

    # Get model from workspace
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    
    processed = errors = 0

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('_1000.jpg'):
                json_path = os.path.join(output_dir, file.replace('_1000.jpg', '_1000.json'))
                
                if os.path.exists(json_path):
                    continue  # Skip silently

                file_path = os.path.join(root, file)
                try:
                    prediction = model.predict(file_path, confidence=confidence, overlap=overlap).json()
                    with open(json_path, 'w') as json_file:
                        json.dump(prediction, json_file)
                    processed += 1
                    print(f"Processed: {file}")
                except Exception as e:
                    errors += 1
                    print(f"Error: {file} - {str(e)}")
    
    print(f"Complete. Processed: {processed}, Errors: {errors}")

