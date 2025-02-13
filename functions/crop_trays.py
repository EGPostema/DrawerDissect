import os
import json
from PIL import Image, ImageFile
from multiprocessing import Pool, cpu_count

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def find_original_file(fullsize_dir, base_name):
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    for ext in supported_formats:
        path = os.path.join(fullsize_dir, f"{base_name}{ext}")
        if os.path.exists(path):
            return path
    return None

def process_image(args):
    fullsize_dir, resized_dir, trays_dir, resized_filename = args
    
    base_name = os.path.splitext(resized_filename)[0].replace('_1000', '')
    base_folder_path = os.path.join(trays_dir, base_name)
    
    if os.path.exists(base_folder_path) and any(fname.endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png')) for fname in os.listdir(base_folder_path)):
        return f"Skipping {base_name} as tray images already exist."

    original_image_path = find_original_file(fullsize_dir, base_name)
    if not original_image_path:
        return f"Warning: Original image file for '{base_name}' not found. Skipping..."

    resized_image_path = os.path.join(resized_dir, resized_filename)
    json_file_path = os.path.join(resized_dir, 'coordinates', f"{base_name}_1000.json")

    if not os.path.exists(json_file_path):
        return f"Warning: JSON file '{json_file_path}' not found for {base_name}. Skipping..."

    with open(json_file_path, 'r') as file:
        annotations = json.load(file)['predictions']

    with Image.open(original_image_path) as original_img, Image.open(resized_image_path) as resized_img:
        if original_img.mode in ('RGBA', 'LA') or (original_img.mode == 'P' and 'transparency' in original_img.info):
            original_img = original_img.convert('RGB')
            
        scale_x = original_img.width / resized_img.width
        scale_y = original_img.height / resized_img.height

        os.makedirs(base_folder_path, exist_ok=True)

        for i, annotation in enumerate(annotations, 1):
            xmin = int((annotation['x'] - annotation['width'] / 2) * scale_x)
            ymin = int((annotation['y'] - annotation['height'] / 2) * scale_y)
            xmax = int((annotation['x'] + annotation['width'] / 2) * scale_x)
            ymax = int((annotation['y'] + annotation['height'] / 2) * scale_y)

            cropped_img = original_img.crop((xmin, ymin, xmax, ymax))
            original_ext = os.path.splitext(original_image_path)[1]
            cropped_image_path = os.path.join(base_folder_path, f'{base_name}_tray_{i:02}{original_ext}')
            cropped_img.save(cropped_image_path, quality=95)

    return f"Processed {base_name} and saved trays."

def crop_trays_from_fullsize(fullsize_dir, resized_dir, trays_dir):
    resized_filenames = [f for f in os.listdir(resized_dir) if f.endswith('_1000.jpg')]
    tasks = [(fullsize_dir, resized_dir, trays_dir, resized_filename) for resized_filename in resized_filenames]

    with Pool(cpu_count()) as pool:
        results = pool.map(process_image, tasks)

    for result in results:
        print(result)



