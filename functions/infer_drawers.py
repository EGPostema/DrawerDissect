import os
import json
from roboflow import Roboflow

def infer_drawers(input_dir, output_dir, rf_instance, workspace_instance, model_endpoint, version, confidence=50, overlap=50):
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
                
                raw_prediction = model.predict(file_path, confidence=confidence, overlap=overlap)
                prediction = raw_prediction.json()
                
                with open(json_path, 'w') as json_file:
                    json.dump(prediction, json_file)








