import os
import json
import time
from roboflow import Roboflow

def infer_patterns(input_dir, output_dir, api_key, model_endpoint, version):
    start_time = time.time()
    
    rf = Roboflow(api_key=api_key)
    project = rf.workspace().project(model_endpoint)
    model = project.version(version).model

    # Loop through the input directory and process each .jpg file
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.jpg'):
                # Determine the relative path from input_dir and use it to create a matching output path
                relative_path = os.path.relpath(root, input_dir)
                json_subfolder = os.path.join(output_dir, relative_path)
                os.makedirs(json_subfolder, exist_ok=True)

                # Define the .json file path in the mirrored folder structure
                json_path = os.path.join(json_subfolder, file.replace('.jpg', '.json'))

                # Check if the .json file already exists
                if os.path.exists(json_path):
                    print(f"'{file}' has already been inferenced, skipping...")
                    continue

                # Full path to the image file
                file_path = os.path.join(root, file)

                # Run inference on the image and save the predictions to the corresponding .json file
                try:
                    prediction = model.predict(file_path).json()

                    with open(json_path, 'w') as json_file:
                        json.dump(prediction, json_file)

                    print(f"Processed {file} and saved predictions to {json_path}")

                except Exception as e:
                    print(f"Error processing {file}: {e}")

    elapsed_time = time.time() - start_time
    print(f"Inference complete. Total time: {elapsed_time:.2f} seconds.")
