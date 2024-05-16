import os
import json
from roboflow import Roboflow

def infer_drawers(input_dir, api_key='YOUR_API_KEY', model_endpoint='YOUR_MODEL_ENDPOINT', version=1, confidence=50, overlap=50):
    rf = Roboflow(api_key=api_key)
    project = rf.workspace().project(model_endpoint)
    model = project.version(version).model

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".jpg"):
                file_path = os.path.join(root, file)
                prediction = model.predict(file_path, confidence=confidence, overlap=overlap).json()
                # Save the prediction as a JSON file
                json_path = file_path.replace('.jpg', '.json')
                with open(json_path, 'w') as json_file:
                    json.dump(prediction, json_file)

if __name__ == '__main__':
    infer_drawers('data/drawers/resized')

