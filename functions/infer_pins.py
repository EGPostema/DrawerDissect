import os
import json
import time
import pandas as pd
from roboflow import Roboflow

def infer_pins(input_dir, output_dir, csv_path, rf_instance, workspace_instance, model_endpoint, version, confidence=50):
    """
    Infer pin locations in masked specimen images using Roboflow model.
    
    Args:
        input_dir (str): Directory containing input images
        output_dir (str): Directory to save prediction JSONs
        csv_path (str): Path to measurements CSV file for filtering
        rf_instance: Initialized Roboflow instance
        workspace_instance: Initialized Roboflow workspace
        model_endpoint (str): Name of the Roboflow model
        version (int): Version number of the model
        confidence (int): Confidence threshold (0-100)
    """
    start_time = time.time()
    
    # Load and filter the CSV file based only on mask_OK condition
    data = pd.read_csv(csv_path)
    filtered_data = data[data['mask_OK'] == 'Y']
    
    # Create a set of full_id values for quick lookup
    valid_ids = set(filtered_data['full_id'])
    
    # Get model from workspace
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    
    # Walk through the input directory and search for .png files in subdirectories
    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('_masked.png'):
                continue  # Skip files that don't match the expected naming convention
            
            # Extract full_id from the filename
            full_id = file.replace('_masked.png', '')
            
            # Check if the full_id is in the valid set from the CSV
            if full_id not in valid_ids:
                continue  # Skip files not meeting the criteria
                
            # Mirror the folder structure in the output directory
            relative_path = os.path.relpath(root, input_dir)
            output_subfolder = os.path.join(output_dir, relative_path)
            os.makedirs(output_subfolder, exist_ok=True)
            
            # Define output .json filename
            json_filename = file.replace('.png', '.json')
            json_path = os.path.join(output_subfolder, json_filename)
            
            # Skip if the .json file already exists
            if os.path.exists(json_path):
                print(f"'{json_path}' already exists, skipping inference for {file}")
                continue
                
            # Full path to the image file
            file_path = os.path.join(root, file)
            
            try:
                # Run inference using Roboflow's model and get prediction results
                prediction = model.predict(file_path, confidence=confidence).json()
                
                # Save prediction results to .json file
                with open(json_path, 'w') as json_file:
                    json.dump(prediction, json_file)
                print(f"Processed {file} and saved predictions to {json_path}")
            except Exception as e:
                print(f"Error processing {file}: {e}")
    
    elapsed_time = time.time() - start_time
    print(f"Inference complete. Total time: {elapsed_time:.2f} seconds.")


