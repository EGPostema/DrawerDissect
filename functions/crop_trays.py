import os
import json
import time
from PIL import Image, ImageFile

# Adjust the max image pixels limit
Image.MAX_IMAGE_PIXELS = None  # Remove the limit entirely
ImageFile.LOAD_TRUNCATED_IMAGES = True  # Allow loading of truncated images

def crop_trays_from_fullsize(fullsize_dir, resized_dir, trays_dir):
    start_time = time.time()  # Start the timer

    coordinates_dir = os.path.join(resized_dir, 'coordinates')
    cropped_count = 0  # Initialize a counter for cropped specimens
    
    # Iterate through resized images
    for resized_filename in os.listdir(resized_dir):
        if resized_filename.endswith('_1000.jpg'):  # Ensure we are processing the correct JPEG images
            base_name = '_'.join(resized_filename.split('_')[:3])
            # Search for the matching original file in the fullsize directory
            original_filename = None
            for filename in os.listdir(fullsize_dir):
                if filename.startswith(base_name) and filename.endswith('.jpg'):
                    original_filename = filename
                    break
            
            if not original_filename:
                print(f"Warning: Original image file starting with '{base_name}' not found. Skipping...")
                continue

            original_image_path = os.path.join(fullsize_dir, original_filename)
            resized_image_path = os.path.join(resized_dir, resized_filename)
            json_filename = resized_filename.replace('.jpg', '.json')
            json_file_path = os.path.join(coordinates_dir, json_filename)

            # Check if the JSON file exists
            if not os.path.exists(json_file_path):
                print(f"Warning: JSON file '{json_file_path}' not found for {base_name}. Skipping...")
                continue

            # Load the JSON data
            with open(json_file_path, 'r') as file:
                data = json.load(file)
                annotations = data['predictions']

            with Image.open(original_image_path) as original_img, Image.open(resized_image_path) as resized_img:
                # Calculate scale factors
                scale_x = original_img.width / resized_img.width
                scale_y = original_img.height / resized_img.height

                # Crop images based on scaled coordinates and save
                for i, annotation in enumerate(annotations, 1):
                    x = annotation['x'] - annotation['width'] / 2
                    y = annotation['y'] - annotation['height'] / 2
                    width = annotation['width']
                    height = annotation['height']

                    xmin = int(x * scale_x)
                    ymin = int(y * scale_y)
                    xmax = int((x + width) * scale_x)
                    ymax = int((y + height) * scale_y)

                    # Crop the image
                    cropped_img = original_img.crop((xmin, ymin, xmax, ymax))

                    # Format the file name with leading zeros
                    formatted_number = f'{i:02}'  # Pad with zeros (e.g., 01, 02, ...)
                    cropped_image_path = os.path.join(trays_dir, f'{base_name}_tray_{formatted_number}.jpg')
                    cropped_img.save(cropped_image_path)

    end_time = time.time()  # End the timer
    elapsed_time = end_time - start_time
    print(f"Processing complete. {cropped_count} trays are saved in the '{trays_dir}' folder. Total time: {elapsed_time:.2f} seconds.")
