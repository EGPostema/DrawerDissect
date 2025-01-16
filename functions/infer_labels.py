import os
import json
import time
from roboflow import Roboflow

def infer_tray_labels(input_dir, output_dir, rf_instance, workspace_instance, model_endpoint, version, confidence=50, overlap=50):
    start_time = time.time()  # Start the timer
    os.makedirs(output_dir, exist_ok=True)
    project = rf_instance.workspace().project(model_endpoint)
    model = project.version(version).model

    for root, _, files in os.walk(input_dir):  # Fixed typo in *dir
        for file in files:
            if file.endswith('_1000.jpg'):
                json_path = os.path.join(output_dir, file.replace('_1000.jpg', '_1000_label.json'))
                
                if os.path.exists(json_path):
                    print(f"'{file}' already has label coordinates, skipping...")
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

