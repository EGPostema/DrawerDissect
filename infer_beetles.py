import os
import json
from roboflow import Roboflow

def infer_beetles(input_dir, output_dir, api_key, model_endpoint, version, confidence=50, overlap=50):
    os.makedirs(output_dir, exist_ok=True)
    rf = Roboflow(api_key=api_key)
    project = rf.workspace().project(model_endpoint)
    model = project.version(version).model

    for root, _, files in os.walk(input_dir):
        for filename in files:
            if filename.endswith('.jpg'):
                image_path = os.path.join(root, filename)
                prediction = model.predict(image_path, confidence=confidence, overlap=overlap).json()

                base_name = os.path.splitext(filename)[0]
                output_path = os.path.join(output_dir, f"{base_name}.json")

                with open(output_path, 'w') as f:
                    json.dump(prediction, f, indent=4)

    print(f"JSON files for beetles generated in {output_dir}")

if __name__ == "__main__":
    API_KEY = "YOUR_API_KEY"
    MODEL_ENDPOINT = "beetlefinder"
    VERSION = "v7"
    infer_beetles('drawers/resized_trays', 'drawers/resized_trays/coordinates', API_KEY, MODEL_ENDPOINT, VERSION)
