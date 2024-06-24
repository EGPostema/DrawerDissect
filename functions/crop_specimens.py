import os
import json
import time
from PIL import Image, ImageFile
from multiprocessing import Pool, cpu_count

# Allow pillow to handle large files
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Organize directories/file-handling and skip any images that have already been processed
def process_tray(args):
    trays_dir, resized_trays_dir, specimens_dir, root, resized_filename = args
    base_name = resized_filename.replace('_1000.jpg', '')
    original_filename = base_name + '.jpg'
    relative_path = os.path.relpath(root, resized_trays_dir)
    original_image_path = os.path.join(trays_dir, relative_path, original_filename)
    resized_image_path = os.path.join(root, resized_filename)
    coordinates_dir = os.path.join(resized_trays_dir, 'coordinates')
    json_filename = resized_filename.replace('.jpg', '.json')
    json_file_path = os.path.join(coordinates_dir, json_filename)

    if not os.path.exists(json_file_path):
        return f"Warning: JSON file '{json_file_path}' not found for {base_name}. Skipping..."

    if not os.path.exists(original_image_path):
        return f"Warning: Original image '{original_image_path}' not found for {base_name}. Skipping..."

    with open(json_file_path, 'r') as file:
        annotations = json.load(file)['predictions']

    tray_number = base_name.split('_')[-1]
    specimen_folder = os.path.join(specimens_dir, relative_path, tray_number)

    # Check if the specimen folder already contains images, skip if already processed
    if os.path.exists(specimen_folder) and any(fname.endswith('.jpg') for fname in os.listdir(specimen_folder)):
        return f"Skipping tray {base_name} as specimens already exist in {specimen_folder}."
    
    # Rescale bounding boxes from .json file from compressed image to fullsize image 
    with Image.open(original_image_path) as original_img:
        with Image.open(resized_image_path) as resized_img:
            scale_x = original_img.width / resized_img.width
            scale_y = original_img.height / resized_img.height

            os.makedirs(specimen_folder, exist_ok=True)

            cropped_count = 0
            for i, annotation in enumerate(annotations, 1):
                x, y, width, height = annotation['x'], annotation['y'], annotation['width'], annotation['height']
                xmin = max(int((x - width / 2 - 5) * scale_x), 0)
                ymin = max(int((y - height / 2 - 5) * scale_y), 0)
                xmax = min(int((x + width / 2 + 5) * scale_x), original_img.width)
                ymax = min(int((y + height / 2 + 5) * scale_y), original_img.height)

                # crop images based on rescaled coordinates, saving as specimen 01, 02... etc.
                cropped_img = original_img.crop((xmin, ymin, xmax, ymax))
                cropped_image_path = os.path.join(specimen_folder, f'{base_name}_spec_{i:03}.jpg')

                cropped_img.save(cropped_image_path)
                cropped_count += 1

    return f"Processed {base_name} and saved {cropped_count} specimens."

def crop_specimens_from_trays(trays_dir, resized_trays_dir, specimens_dir):
    start_time = time.time()  # Start the timer

    tasks = []
    for root, _, files in os.walk(resized_trays_dir):
        for resized_filename in files:
            if resized_filename.endswith('_1000.jpg'):
                tasks.append((trays_dir, resized_trays_dir, specimens_dir, root, resized_filename))

    # Use multiprocessing to process images in parallel
    with Pool(cpu_count()) as pool:
        results = pool.map(process_tray, tasks)

    for result in results:
        print(result)

    elapsed_time = time.time() - start_time
    print(f"Processing complete. Total time: {elapsed_time:.2f} seconds.")
