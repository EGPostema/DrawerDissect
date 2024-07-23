import os
import json
import csv
import time
from roboflow import Roboflow

def infer_beetles(input_dir, output_dir, api_key, model_endpoint, version, confidence=50, overlap=50):
	start_time = time.time()
	os.makedirs(output_dir, exist_ok=True)

	rf = Roboflow(api_key=api_key)
	project = rf.workspace().project(model_endpoint)
	model = project.version(version).model

	for root, _, files in os.walk(input_dir):
		for file in files:
			json_path = os.path.join(output_dir, file.replace('.jpg', '.json'))

			if os.path.exists(json_path):
				print(f"'{file}' has already been inferenced, skipping...")
				continue

			file_path = os.path.join(root, file)
			try:
				prediction = model.predict(file_path, confidence = confidence).json()

				json_file = open(json_path, 'w')

				json.dump(prediction, json_file)

				print(f"Processed {file} and saved predictions to {json_path}")

			except Exception as e:
				print(f"Error processing {file}: {e}")

	elapsed_time = time.time() - start_time
	print(f"Inference complete. Total time: {elapsed_time:.2f} seconds.")
