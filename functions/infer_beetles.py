import os
import json
import time
from roboflow import Roboflow
from typing import Optional

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
    Infer beetle segmentation masks using Roboflow model.
    
    Args:
        input_dir (str): Directory containing input images
        output_dir (str): Directory to save prediction JSONs
        rf_instance: Initialized Roboflow instance
        workspace_instance: Initialized Roboflow workspace
        model_endpoint (str): Name of the Roboflow model
        version (int): Version number of the model
        confidence (float, optional): Confidence threshold (0-100)
    """
    start_time = time.time()
    
    # Get model from workspace
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    
    processed = 0
    errors = 0
    
    for root, _, files in os.walk(input_dir):
        jpg_files = [f for f in files if f.endswith('.jpg')]
        if not jpg_files:
            continue
            
        relative_path = os.path.relpath(root, input_dir)
        path_parts = relative_path.split(os.sep)
        
        if len(path_parts) < 2:
            print(f"Skipping invalid folder structure: {root}")
            continue
            
        drawer_id, tray_number = path_parts[:2]
        output_subfolder = os.path.join(output_dir, drawer_id, tray_number)
        os.makedirs(output_subfolder, exist_ok=True)
        
        for file in jpg_files:
            json_path = os.path.join(output_subfolder, file.replace('.jpg', '.json'))
            
            if os.path.exists(json_path):
                print(f"Skipping existing: {json_path}")
                continue
                
            try:
                file_path = os.path.join(root, file)
                prediction = model.predict(file_path, confidence=confidence).json()
                
                with open(json_path, 'w') as f:
                    json.dump(prediction, f, indent=2)
                
                processed += 1
                print(f"Processed: {file}")
                
            except Exception as e:
                errors += 1
                print(f"Error processing {file}: {str(e)}")
                continue
    
    elapsed = time.time() - start_time
    print(f"Complete in {elapsed:.2f}s. Processed: {processed}, Errors: {errors}")







