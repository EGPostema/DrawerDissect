import os
import json
import time
from roboflow import Roboflow

def infer_tray_images(input_dir, output_dir, rf_instance, workspace_instance, model_endpoint, version, confidence=50, overlap=50):
    """
    Infer specimen locations in tray images using Roboflow model.
    
    Args:
        input_dir (str): Directory containing input images
        output_dir (str): Directory to save prediction JSONs
        rf_instance: Initialized Roboflow instance 
        workspace_instance: Initialized Roboflow workspace
        model_endpoint (str): Name of the Roboflow model
        version (int): Version number of the model
        confidence (int): Confidence threshold (0-100)
        overlap (int): Overlap threshold for NMS (0-100)
    """
    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)

    # Get model from workspace
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('_1000.jpg'):
                json_path = os.path.join(output_dir, file.replace('_1000.jpg', '_1000.json'))
                
                if os.path.exists(json_path):
                    print(f"'{file}' already has specimen coordinates, skipping...")
                    continue

                file_path = os.path.join(root, file)
                try:
                    prediction = model.predict(file_path, confidence=confidence, overlap=overlap).json()
                    with open(json_path, 'w') as json_file:
                        json.dump(prediction, json_file)
                    print(f"Processed {file} and saved predictions to {json_path}")
                except Exception as e:
                    print(f"Error processing {file}: {e}")

    elapsed_time = time.time() - start_time
    print(f"Inference complete. Total time: {elapsed_time:.2f} seconds.")

