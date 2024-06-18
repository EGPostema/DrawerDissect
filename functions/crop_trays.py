import os
import json
import time
from PIL import Image, ImageFile

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def crop_trays_from_fullsize(fullsize_dir, resized_dir, trays_dir):
    start_time = time.time()  # Start the timer

    coordinates_dir = os.path.join(resized_dir, 'coordinates')
    cropped_count = 0  # Initialize a counter for cropped trays
    
    # Iterate through resized images
    for resized_filename in os.listdir(resized_dir):
        if resized_filename.endswith('_1000.jpg'):  # Ensure we are processing the correct JPEG images
            base_name = '_'.join(resized_filename.split('_')[:3])

            # Search for the matching original file in the fullsize directory
            original_filename = next((f for f in os.listdir(fullsize_dir) if f.startswith(base_name) and f.endswith('.jpg')), None)
            
            if not original_filename:
                print(f"Warning: Original image file starting with '{base_name}' not found. Skipping...")
                continue

            original_image_path = os.path.join(fullsize_dir, original_filename)
            resized_image_path = os.path.join(resized_dir, resized_filename)
            json_file_path = os.path.join(coordinates_dir, resized_filename.replace('.jpg', '.json'))

            if not os.path.exists(json_file_path):
                print(f"Warning: JSON file '{json_file_path}' not found for {base_name}. Skipping...")
                continue

            with open(json_file_path, 'r') as file:
                annotations = json.load(file)['predictions']

            with Image.open(original_image_path) as original_img, Image.open(resized_image_path) as resized_img:
                # Calculate scale factors
                scale_x = original_img.width / resized_img.width
                scale_y = original_img.height / resized_img.height

                # Create a subfolder for the base name if it doesn't exist
                base_folder_path = os.path.join(trays_dir, base_name)
                os.makedirs(base_folder_path, exist_ok=True)

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

                    cropped_img = original_img.crop((xmin, ymin, xmax, ymax))
                    cropped_image_path = os.path.join(base_folder_path, f'{base_name}_tray_{i:02}.jpg')
                    cropped_img.save(cropped_image_path)
                    cropped_count += 1
                    
    elapsed_time = time.time() - start_time
    print(f"Processing complete. {cropped_count} trays are saved in the '{trays_dir}' folder. Total time: {elapsed_time:.2f} seconds.")
