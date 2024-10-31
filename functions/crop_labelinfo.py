import os
import json
import time
from PIL import Image, ImageFile
from multiprocessing import Pool, cpu_count

# Configure PIL settings for large and truncated images
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def process_label(args):
    trays_dir, resized_trays_dir, label_coordinates_dir, labels_output_dir, root, resized_filename = args
    base_name = resized_filename.replace('_1000.jpg', '')
    original_filename = base_name + '.jpg'
    relative_path = os.path.relpath(root, resized_trays_dir)
    original_image_path = os.path.join(trays_dir, relative_path, original_filename)
    resized_image_path = os.path.join(root, resized_filename)
    json_filename = resized_filename.replace('.jpg', '.json')
    json_file_path = os.path.join(label_coordinates_dir, json_filename)

    # Check if necessary files exist
    if not os.path.exists(json_file_path):
        return f"Warning: JSON file '{json_file_path}' not found for {base_name}. Skipping..."

    if not os.path.exists(original_image_path):
        return f"Warning: Original image '{original_image_path}' not found for {base_name}. Skipping..."

    # Load label coordinates from JSON
    with open(json_file_path, 'r') as file:
        annotations = json.load(file)['predictions']

    # Filter for 'barcode' and 'label' classes
    barcode_annotations = [a for a in annotations if a['class'] == 'barcode']
    label_annotations = [a for a in annotations if a['class'] == 'label']

    # Skip if no 'barcode' or 'label' annotations
    if not barcode_annotations and not label_annotations:
        return f"Skipping {base_name} as no 'barcode' or 'label' predictions were found."

    # Open the full-size and resized images for scaling
    with Image.open(original_image_path) as original_img:
        with Image.open(resized_image_path) as resized_img:
            scale_x = original_img.width / resized_img.width
            scale_y = original_img.height / resized_img.height

            # Ensure output directory exists
            os.makedirs(labels_output_dir, exist_ok=True)

            cropped_count = 0
            for i, annotation in enumerate(barcode_annotations + label_annotations, 1):
                x, y, width, height = annotation['x'], annotation['y'], annotation['width'], annotation['height']
                xmin = max(int((x - width / 2 - 5) * scale_x), 0)
                ymin = max(int((y - height / 2 - 5) * scale_y), 0)
                xmax = min(int((x + width / 2 + 5) * scale_x), original_img.width)
                ymax = min(int((y + height / 2 + 5) * scale_y), original_img.height)

                # Set file extension based on class
                if annotation['class'] == 'barcode':
                    extension = "_code.jpg"
                elif annotation['class'] == 'label':
                    extension = "_label.jpg"
                
                # Save cropped image with appropriate extension
                cropped_img = original_img.crop((xmin, ymin, xmax, ymax))
                cropped_image_path = os.path.join(labels_output_dir, f'{base_name}_{i:03}{extension}')
                cropped_img.save(cropped_image_path)
                cropped_count += 1

    return f"Processed {base_name} and saved {cropped_count} crops."

def crop_info_from_trays(trays_dir, resized_trays_dir, label_coordinates_dir, labels_output_dir):
    start_time = time.time()  # Start the timer

    tasks = []
    for root, _, files in os.walk(resized_trays_dir):
        for resized_filename in files:
            if resized_filename.endswith('_1000.jpg'):
                tasks.append((trays_dir, resized_trays_dir, label_coordinates_dir, labels_output_dir, root, resized_filename))

    # Use multiprocessing to process images in parallel
    with Pool(cpu_count()) as pool:
        results = pool.map(process_label, tasks)

    for result in results:
        print(result)

    elapsed_time = time.time() - start_time
    print(f"Processing complete. Total time: {elapsed_time:.2f} seconds.")
