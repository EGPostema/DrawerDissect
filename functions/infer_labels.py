import os
import json
import time
import tempfile
from PIL import Image
from contextlib import contextmanager
from roboflow import Roboflow

@contextmanager
def temporary_jpg_if_needed(image_path):
    """Creates temporary JPG version if image is TIFF."""
    if image_path.lower().endswith(('.jpg', '.jpeg', '.png')):
        yield image_path
    else:  # Handle TIFFs
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=True) as tmp:
            with Image.open(image_path) as img:
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    img = img.convert('RGB')
                img.save(tmp.name, 'JPEG', quality=95)
            yield tmp.name

def infer_tray_labels(input_dir, output_dir, rf_instance, workspace_instance, model_endpoint, version, confidence=50, overlap=50):
    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)
    project = rf_instance.workspace().project(model_endpoint)
    model = project.version(version).model

    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('_1000.jpg'):
                continue

            json_path = os.path.join(output_dir, file.replace('_1000.jpg', '_1000_label.json'))
            if os.path.exists(json_path):
                print(f"'{file}' already has label coordinates, skipping...")
                continue

            file_path = os.path.join(root, file)
            try:
                with temporary_jpg_if_needed(file_path) as inference_path:
                    prediction = model.predict(inference_path, confidence=confidence, overlap=overlap).json()
                with open(json_path, 'w') as json_file:
                    json.dump(prediction, json_file)
                print(f"Processed {file} and saved predictions to {json_path}")
            except Exception as e:
                print(f"Error processing {file}: {e}")

    elapsed_time = time.time() - start_time
    print(f"Inference complete. Total time: {elapsed_time:.2f} seconds.")
