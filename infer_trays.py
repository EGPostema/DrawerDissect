import os
import json
from roboflow import Roboflow

def infer_tray_images(input_dir, output_dir, api_key, model_endpoint, version, confidence=50, overlap=50):
    os.makedirs(output_dir, exist_ok=True)
    rf = Roboflow(api_key=api_key)
    project = rf.workspace().project(model_endpoint)
    model = project.version(version).model

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('_1000.jpg'):
                file_path = os.path.join(root, file)
                prediction = model.predict(file_path, confidence=confidence, overlap=overlap).json()
                json_path = os.path.join(output_dir, file.replace('.jpg', '.json'))
                with open(json_path, 'w') as json_file:
                    json.dump(prediction, json_file)

if __name__ == '__main__':
    infer_tray_images('coloroptera/drawers/resized_trays', 'coloroptera/drawers/resized_trays/coordinates', 'YOUR_API_KEY', 'YOUR_TRAY_MODEL_ENDPOINT', 1)

