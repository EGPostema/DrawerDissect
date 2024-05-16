# READ COORDINATES FROM .JSON FILE, RESCALE TO FULLSIZE IMAGE, AND CROP INTO SEPARATE TRAYS

import os
import json
import time
from PIL import Image, ImageFile

# Adjust the max image pixels limit
Image.MAX_IMAGE_PIXELS = None  # Remove the limit entirely
ImageFile.LOAD_TRUNCATED_IMAGES = True  # Allow loading of truncated images

def process_images():
    start_time = time.time()  # Start the timer

    original_image_folder = 'fullsize'
    resized_image_folder = 'resized'
    json_file_path = os.path.join(resized_image_folder, 'coordinates', '_annotations.coco.json')  # Single JSON file path
    output_folder = 'trays'  # Folder for cropped images

    # Check if the JSON file exists
    if not os.path.exists(json_file_path):
        print(f"Error: JSON file '{json_file_path}' not found.")
        return

    # Load the JSON data
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Build a mapping from image_id to file_name and annotations
    image_id_to_filename = {image['id']: image['file_name'] for image in data['images']}
    image_id_to_annotations = {}
    for annotation in data['annotations']:
        image_id = annotation['image_id']
        if image_id not in image_id_to_annotations:
            image_id_to_annotations[image_id] = []
        image_id_to_annotations[image_id].append(annotation['bbox'])

    # Create a dictionary to map base names to their respective IDs
    base_name_to_id = {}
    for image_id, file_name in image_id_to_filename.items():
        base_name = os.path.splitext(file_name)[0].split('_1000')[0]
        base_name_to_id[base_name] = image_id

    # Iterate through resized images
    for resized_filename in os.listdir(resized_image_folder):
        if resized_filename.endswith('.jpg'):  # Ensure we are processing JPEG images
            base_name = os.path.splitext(resized_filename)[0].replace('_1000', '')
            original_filename = base_name + '.jpg'
            original_image_path = os.path.join(original_image_folder, original_filename)
            resized_image_path = os.path.join(resized_image_folder, resized_filename)

            # Find the corresponding image ID from the JSON file
            if base_name not in base_name_to_id:
                print(f"Warning: No annotations found for {base_name}. Skipping...")
                continue

            image_id = base_name_to_id[base_name]

            if image_id not in image_id_to_annotations:
                print(f"Warning: No annotations found for {file_name}. Skipping...")
                continue

            with Image.open(original_image_path) as original_img, Image.open(resized_image_path) as resized_img:
                annotations = image_id_to_annotations[image_id]

                # Calculate scale factors
                scale_x = original_img.width / resized_img.width
                scale_y = original_img.height / resized_img.height

                # Crop images based on scaled coordinates and save
                for i, bbox in enumerate(annotations, 1):
                    xmin = int(bbox[0] * scale_x)
                    xmax = int((bbox[0] + bbox[2]) * scale_x)
                    ymin = int(bbox[1] * scale_y)
                    ymax = int((bbox[1] + bbox[3]) * scale_y)

                    # Crop the image
                    cropped_img = original_img.crop((xmin, ymin, xmax, ymax))

                    # Format the file name with leading zeros
                    formatted_number = f'{i:02}'  # Pad with zeros (e.g., 01, 02, ...)
                    cropped_image_path = os.path.join(output_folder, f'{base_name}_tray_{formatted_number}.jpg')
                    cropped_img.save(cropped_image_path)

    end_time = time.time()  # End the timer
    elapsed_time = end_time - start_time
    print(f"Processing complete. Cropped images are saved in the 'trays' folder. Total time: {elapsed_time:.2f} seconds.")

# Run the processing function
process_images()
