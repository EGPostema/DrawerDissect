import os
import json
import time
from roboflow import Roboflow

def infer_beetles(input_dir, output_dir, api_key, model_endpoint, version, confidence=50):
    start_time = time.time()

    # Initialize Roboflow model
    rf = Roboflow(api_key=api_key)
    project = rf.workspace().project(model_endpoint)
    model = project.version(version).model

    # Walk through the input directory and search for .jpg files in all subdirectories
    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('.jpg'):
                continue  # Skip non-JPG files

            # Construct the relative path to maintain folder structure
            relative_path = os.path.relpath(root, input_dir)
            path_parts = relative_path.split(os.sep)

            # Ensure there are enough parts to identify the drawer and tray
            if len(path_parts) < 2:
                print(f"Skipping file due to invalid folder structure: {file}")
                continue

            drawer_id = path_parts[0]  # First part of the path as drawer ID
            tray_number = path_parts[1]  # Second part as tray ID

            # Construct output folder and ensure it exists
            output_subfolder = os.path.join(output_dir, drawer_id, tray_number)
            os.makedirs(output_subfolder, exist_ok=True)

            # Construct the output .json filename based on the input .jpg file
            json_filename = file.replace('.jpg', '.json')
            json_path = os.path.join(output_subfolder, json_filename)

            # Check if the .json file already exists, and skip if it does
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








