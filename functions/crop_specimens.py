import os
import json
import time
from PIL import Image, ImageFile

# Adjust the max image pixels limit
Image.MAX_IMAGE_PIXELS = None  # Remove the limit entirely
ImageFile.LOAD_TRUNCATED_IMAGES = True  # Allow loading of truncated images

def crop_specimens_from_trays(trays_dir, resized_trays_dir, specimens_dir):
    start_time = time.time()  # Start the timer

    resized_trays_coordinates_dir = os.path.join(resized_trays_dir, 'coordinates')

    # Iterate through resized images
    for resized_filename in os.listdir(resized_trays_dir):
        if resized_filename.endswith('_1000.jpg'):  # Ensure we are processing the correct JPEG images
            base_name = os.path.splitext(resized_filename)[0].replace('_1000', '')
            original_filename = base_name + '.jpg'
            original_image_path = os.path.join(trays_dir, original_filename)
            resized_image_path = os.path.join(resized_trays_dir, resized_filename)
            json_filename = resized_filename.replace('.jpg', '.json')
            json_file_path = os.path.join(resized_trays_coordinates_dir, json_filename)

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

                # Crop images based on scaled coordinates, adding a 50 pixel buffer, and save
                for i, annotation in enumerate(annotations, 1):
                    x = annotation['x'] - annotation['width'] / 2
                    y = annotation['y'] - annotation['height'] / 2
                    width = annotation['width']
                    height = annotation['height']

                    xmin = max(int((x - 5) * scale_x), 0)
                    ymin = max(int((y - 5) * scale_y), 0)
                    xmax = min(int((x + width + 5) * scale_x), original_img.width)
                    ymax = min(int((y + height + 5) * scale_y), original_img.height)

                    # Crop the image
                    cropped_img = original_img.crop((xmin, ymin, xmax, ymax))

                    # Format the file name with leading zeros
                    formatted_number = f'{i:03}'  # Pad with zeros (e.g., 001, 002, ...)
                    cropped_image_path = os.path.join(specimens_dir, f'{base_name}_spec_{formatted_number}.jpg')
                    cropped_img.save(cropped_image_path)

    end_time = time.time()  # End the timer
    elapsed_time = end_time - start_time
    print(f"Processing complete. Cropped specimens are saved in the '{specimens_dir}' folder. Total time: {elapsed_time:.2f} seconds.")
