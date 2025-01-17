import os
import json
import time
from roboflow import Roboflow

def infer_drawers(input_dir, output_dir, rf_instance, workspace_instance, model_endpoint, version, confidence=50, overlap=50):
    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    
    # Safely remove resize preprocessing if it exists
    if hasattr(model, 'preprocessing') and 'resize' in model.preprocessing:
        del model.preprocessing['resize']
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('_1000.jpg'):
                json_path = os.path.join(output_dir, file.replace('.jpg', '.json'))
                
                # Check if JSON file already exists
                if os.path.exists(json_path):
                    print(f"'{file}' already has tray coordinates, skipping...")
                    continue
                    
                file_path = os.path.join(root, file)
                
                # Get raw prediction first
                raw_prediction = model.predict(file_path, confidence=confidence, overlap=overlap)
                print("Raw prediction structure:", raw_prediction)
                
                # Convert to JSON
                prediction = raw_prediction.json()
                print("JSON converted prediction:", prediction)
                
                with open(json_path, 'w') as json_file:
                    json.dump(prediction, json_file)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Inference complete. Total time: {elapsed_time:.2f} seconds.")







