import os
import json
import time
from PIL import Image, ImageFile

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def crop_specimens_from_trays(trays_dir, resized_trays_dir, specimens_dir):
    start_time = time.time()  # Start the timer
    cropped_count = 0  # Initialize counter for new images created

    coordinates_dir = os.path.join(resized_trays_dir, 'coordinates')

    # Iterate through resized images in subdirectories
    for root, _, files in os.walk(resized_trays_dir):
        for resized_filename in files:
            if resized_filename.endswith('_1000.jpg'):
                base_name = resized_filename.replace('_1000.jpg', '')
                original_filename = base_name + '.jpg'
                relative_path = os.path.relpath(root, resized_trays_dir)
                original_image_path = os.path.join(trays_dir, relative_path, original_filename)
                resized_image_path = os.path.join(root, resized_filename)
                json_filename = resized_filename.replace('.jpg', '.json')
                json_file_path = os.path.join(coordinates_dir, json_filename)

                if not os.path.exists(json_file_path):
                    print(f"Warning: JSON file '{json_file_path}' not found for {base_name}. Skipping...")
                    continue

                if not os.path.exists(original_image_path):
                    print(f"Warning: Original image '{original_image_path}' not found for {base_name}. Skipping...")
                    continue

                with open(json_file_path, 'r') as file:
                    annotations = json.load(file)['predictions']

                with Image.open(original_image_path) as original_img:
                    scale_x = original_img.width / Image.open(resized_image_path).width
                    scale_y = original_img.height / Image.open(resized_image_path).height

                    for i, annotation in enumerate(annotations, 1):
                        x, y, width, height = annotation['x'], annotation['y'], annotation['width'], annotation['height']
                        xmin = max(int((x - width / 2 - 5) * scale_x), 0)
                        ymin = max(int((y - height / 2 - 5) * scale_y), 0)
                        xmax = min(int((x + width / 2 + 5) * scale_x), original_img.width)
                        ymax = min(int((y + height / 2 + 5) * scale_y), original_img.height)

                        cropped_img = original_img.crop((xmin, ymin, xmax, ymax))

                        tray_number = base_name.split('_')[-1]
                        specimen_folder = os.path.join(specimens_dir, relative_path, tray_number)
                        os.makedirs(specimen_folder, exist_ok=True)

                        cropped_image_path = os.path.join(specimen_folder, f'{base_name}_spec_{i:03}.jpg')

                        # Check if the cropped image already exists
                        if os.path.exists(cropped_image_path):
                            print(f"Skipping {cropped_image_path}, already exists.")
                            continue

                        cropped_img.save(cropped_image_path)
                        cropped_count += 1

    elapsed_time = time.time() - start_time
    print(f"Processing complete. {cropped_count} specimens are saved in the '{specimens_dir}' folder. Total time: {elapsed_time:.2f} seconds.")

if __name__ == '__main__':
    crop_specimens_from_trays('coloroptera/drawers/trays', 'coloroptera/drawers/resized_trays', 'coloroptera/drawers/specimens')
