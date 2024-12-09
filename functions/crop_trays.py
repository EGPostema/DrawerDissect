import os
import json
import time
from PIL import Image, ImageFile
from multiprocessing import Pool, cpu_count

# Allow processing of large images
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def process_image(args):
    fullsize_dir, resized_dir, trays_dir, resized_filename = args
    
    # Get base name by removing _1000.jpg
    base_name = os.path.splitext(resized_filename)[0].replace('_1000', '')
    
    # Check if the drawer folder already contains tray images
    base_folder_path = os.path.join(trays_dir, base_name)
    if os.path.exists(base_folder_path) and any(fname.endswith('.jpg') for fname in os.listdir(base_folder_path)):
        return f"Skipping {base_name} as tray images already exist."

    # The original file should just be base_name.jpg
    original_filename = f"{base_name}.jpg"
    original_image_path = os.path.join(fullsize_dir, original_filename)
    
    if not os.path.exists(original_image_path):
        return f"Warning: Original image file '{original_filename}' not found. Skipping..."

    resized_image_path = os.path.join(resized_dir, resized_filename)
    coordinates_dir = os.path.join(resized_dir, 'coordinates')
    json_file_path = os.path.join(coordinates_dir, f"{base_name}_1000.json")

    if not os.path.exists(json_file_path):
        return f"Warning: JSON file '{json_file_path}' not found for {base_name}. Skipping..."

    with open(json_file_path, 'r') as file:
        annotations = json.load(file)['predictions']

    with Image.open(original_image_path) as original_img:
        with Image.open(resized_image_path) as resized_img:
            # Calculate scale factors
            scale_x = original_img.width / resized_img.width
            scale_y = original_img.height / resized_img.height

            # Create a subfolder for the base name if it doesn't exist
            os.makedirs(base_folder_path, exist_ok=True)

            # Crop images based on scaled coordinates and save
            for i, annotation in enumerate(annotations, 1):
                xmin = int((annotation['x'] - annotation['width'] / 2) * scale_x)
                ymin = int((annotation['y'] - annotation['height'] / 2) * scale_y)
                xmax = int((annotation['x'] + annotation['width'] / 2) * scale_x)
                ymax = int((annotation['y'] + annotation['height'] / 2) * scale_y)

                cropped_img = original_img.crop((xmin, ymin, xmax, ymax))
                cropped_image_path = os.path.join(base_folder_path, f'{base_name}_tray_{i:02}.jpg')
                cropped_img.save(cropped_image_path)

    return f"Processed {base_name} and saved trays."

def crop_trays_from_fullsize(fullsize_dir, resized_dir, trays_dir):
    start_time = time.time()  # Start the timer

    resized_filenames = [f for f in os.listdir(resized_dir) if f.endswith('_1000.jpg')]
    tasks = [(fullsize_dir, resized_dir, trays_dir, resized_filename) for resized_filename in resized_filenames]

    # Use multiprocessing to process images in parallel
    with Pool(cpu_count()) as pool:
        results = pool.map(process_image, tasks)

    for result in results:
        print(result)

    elapsed_time = time.time() - start_time
    print(f"Processing complete. Total time: {elapsed_time:.2f} seconds.")



