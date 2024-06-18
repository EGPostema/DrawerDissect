import os
import pandas as pd
import json
from PIL import Image
from pytesseract import pytesseract
from roboflow import Roboflow

# Function to call the Roboflow model
def get_detections(image_path, model, confidence, overlap, label_coordinates_dir):
    prediction = model.predict(image_path, confidence=confidence, overlap=overlap).json()
    
    # Save prediction to JSON file
    json_filename = os.path.splitext(os.path.basename(image_path))[0] + '.json'
    json_path = os.path.join(label_coordinates_dir, json_filename)
    with open(json_path, 'w') as json_file:
        json.dump(prediction, json_file)
    
    return prediction, json_filename

# Function to extract text from detected areas using Tesseract
def extract_text_from_area(image, area):
    cropped_img = image.crop((area['x'] - area['width']//2, area['y'] - area['height']//2, area['x'] + area['width']//2, area['y'] + area['height']//2))
    text = pytesseract.image_to_string(cropped_img)
    return text.strip()

# Function to extract label information using detections
def extract_label_info(image_path, model, confidence, overlap, label_coordinates_dir):
    img = Image.open(image_path)
    json_filename = os.path.splitext(os.path.basename(image_path))[0] + '.json'
    json_path = os.path.join(label_coordinates_dir, json_filename)
    
    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            detections = json.load(json_file)
    else:
        detections, json_filename = get_detections(image_path, model, confidence, overlap, label_coordinates_dir)

    if not detections.get('predictions'):
        print(f"No label information found for {os.path.basename(image_path)}, label not transcribed")
        return None

    label_info = {
        'image_file': os.path.basename(image_path),
        'extension': os.path.basename(image_path).replace('_1000.jpg', ''),
        'barcode': '',
        'label': '',
        'geocode': '',
        'json_filename': json_filename
    }

    label_info['extension'] = label_info['extension'][:label_info['extension'].rfind('_')]

    for detection in detections['predictions']:
        if detection['class'] == 'barcode':
            label_info['barcode'] = extract_text_from_area(img, detection)
        elif detection['class'] == 'label':
            label_info['label'] = extract_text_from_area(img, detection)
        elif detection['class'] == 'geocode':
            label_info['geocode'] = extract_text_from_area(img, detection)
    
    return label_info

def transcribe_labels_and_ids(resized_trays_dir, api_key, model_endpoint, version, confidence, overlap):
    rf = Roboflow(api_key=api_key)
    project = rf.workspace().project(model_endpoint)
    model = project.version(version).model

    label_coordinates_dir = os.path.join(resized_trays_dir, 'label_coordinates')
    label_data_directory = os.path.join(resized_trays_dir, 'label_data')
    os.makedirs(label_coordinates_dir, exist_ok=True)
    os.makedirs(label_data_directory, exist_ok=True)
    csv_path = os.path.join(label_data_directory, 'labels.csv')
    
    if os.path.exists(csv_path):
        existing_df = pd.read_csv(csv_path)
        existing_files = set(existing_df['image_file'])
        existing_transcriptions = set(existing_df.dropna(subset=['barcode', 'label', 'geocode'])['image_file'])
    else:
        existing_files = set()
        existing_transcriptions = set()
    
    data = []
    for root, _, files in os.walk(resized_trays_dir):
        for file in files:
            if file.endswith('.jpg') and 'checkpoint' not in file:
                image_path = os.path.join(root, file)
                if file in existing_files:
                    print(f"Image {file} has already been transcribed")
                    continue
                if file in existing_transcriptions:
                    print(f"Transcription for image {file} already exists in CSV")
                    continue
                label_info = extract_label_info(image_path, model, confidence, overlap, label_coordinates_dir)
                if label_info:
                    data.append(label_info)
    
    if data:
        df = pd.DataFrame(data)
        if os.path.exists(csv_path):
            df.to_csv(csv_path, mode='a', header=False, index=False)
        else:
            df.to_csv(csv_path, index=False)
        print(f"Label data saved to {csv_path}")

if __name__ == '__main__':
    transcribe_labels_and_ids('coloroptera/drawers/resized_trays', 'YOUR_API_KEY', 'YOUR_LABEL_MODEL_ENDPOINT', 1)
