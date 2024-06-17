import os
import json
from roboflow import Roboflow

def infer_drawers(input_dir, output_dir, api_key, model_endpoint, version, confidence=50, overlap=50):
    start_time = time.time()  # Start the timer
    os.makedirs(output_dir, exist_ok=True)
    rf = Roboflow(api_key=api_key)
    project = rf.workspace().project(model_endpoint)
    model = project.version(version).model

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('_1000.jpg'):
                json_path = os.path.join(output_dir, file.replace('.jpg', '.json'))
                
                # Check if JSON file already exists
                if os.path.exists(json_path):
                    print(f"'{file}' already has tray coordinates, skipping...")
                    continue

                file_path = os.path.join(root, file)
                prediction = model.predict(file_path, confidence=confidence, overlap=overlap).json()
                with open(json_path, 'w') as json_file:
                    json.dump(prediction, json_file)
                    
    end_time = time.time()  # End the timer
    elapsed_time = end_time - start_time
    print(f"Inference complete. Total time: {elapsed_time:.2f} seconds.")
    
if __name__ == '__main__':
    infer_drawers('coloroptera/drawers/resized', 'coloroptera/drawers/resized/coordinates', 'YOUR_API_KEY', 'YOUR_DRAWER_MODEL_ENDPOINT', 1)


