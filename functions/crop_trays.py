import os
import json
from PIL import Image, ImageFile
from multiprocessing import Pool, cpu_count
from logging_utils import log, log_found, log_progress
from config import DrawerDissectConfig

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def find_original_file(fullsize_dir, base_name):
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    for ext in supported_formats:
        path = os.path.join(fullsize_dir, f"{base_name}{ext}")
        if os.path.exists(path):
            return path
    return None

def determine_optimal_workers(total_files: int, sequential: bool = False, max_workers: int = None) -> int:
    if sequential:
        return 1
    if max_workers is not None:
        return min(max_workers, total_files)
    return min(max(1, cpu_count() // 2), total_files)

def process_image(args):
    fullsize_dir, resized_dir, trays_dir, resized_filename, current, total = args
    
    base_name = os.path.splitext(resized_filename)[0].replace('_1000', '')
    base_folder_path = os.path.join(trays_dir, base_name)
    
    if os.path.exists(base_folder_path) and any(fname.endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png')) for fname in os.listdir(base_folder_path)):
        log_progress("crop_trays", current, total, f"Skipped {base_name} (already exists)")
        return False

    original_image_path = find_original_file(fullsize_dir, base_name)
    if not original_image_path:
        log(f"Warning: Original image file for '{base_name}' not found")
        return False

    resized_image_path = os.path.join(resized_dir, resized_filename)
    json_file_path = os.path.join(resized_dir, 'coordinates', f"{base_name}_1000.json")

    if not os.path.exists(json_file_path):
        log(f"Warning: JSON file not found for {base_name}")
        return False

    try:
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

        log_progress("crop_trays", current, total, f"Processed {base_name} with {len(annotations)} trays")
        return True
    
    except Exception as e:
        log(f"Error processing {base_name}: {str(e)}")
        return False

def crop_trays_from_fullsize(fullsize_dir, resized_dir, trays_dir, sequential=False, max_workers=None, batch_size=None):
    config = DrawerDissectConfig()
    mem_config = config.get_memory_config('crop_trays')
    
    sequential = sequential if sequential is not None else mem_config.get('sequential', False)
    max_workers = max_workers if max_workers is not None else mem_config.get('max_workers')
    batch_size = batch_size if batch_size is not None else mem_config.get('batch_size')
    
    os.makedirs(trays_dir, exist_ok=True)
    resized_filenames = [f for f in os.listdir(resized_dir) if f.endswith('_1000.jpg')]
    
    if not resized_filenames:
        log("No resized images found to process")
        return
        
    log_found("resized images", len(resized_filenames))
    
    tasks = [(fullsize_dir, resized_dir, trays_dir, filename, i+1, len(resized_filenames)) for i, filename in enumerate(resized_filenames)]
    
    num_workers = determine_optimal_workers(len(tasks), sequential, max_workers)
    
    if num_workers > 1 and not sequential:
        with Pool(num_workers) as pool:
            results = pool.map(process_image, tasks)
    else:
        results = [process_image(task) for task in tasks]
    
    processed = sum(results)
    skipped = len(results) - processed
    log(f"Complete. {processed} processed, {skipped} skipped")



