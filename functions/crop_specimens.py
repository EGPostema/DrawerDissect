import os
import json
from PIL import Image, ImageFile
from multiprocessing import Pool, cpu_count
from logging_utils import log, log_found, log_progress

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def process_tray(args):
    trays_dir, resized_trays_dir, specimens_dir, root, resized_filename, current, total = args
    base_name = resized_filename.replace('_1000.jpg', '')
    
    # Find original file with any supported extension
    drawer_name = '_'.join(base_name.split('_')[:-2])
    tray_num = base_name.split('_')[-1]
    drawer_folder = os.path.join(trays_dir, drawer_name)
    
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    original_path = None
    original_ext = None
    
    for ext in supported_formats:
        test_path = os.path.join(drawer_folder, base_name + ext)
        if os.path.exists(test_path):
            original_path = test_path
            original_ext = ext
            break
            
    json_path = os.path.join(resized_trays_dir, 'coordinates', f'{base_name}_1000.json')
    specimen_folder = os.path.join(specimens_dir, drawer_name, tray_num)
    
    if not os.path.exists(json_path):
        log_progress("crop_specimens", current, total, f"Skipped {base_name} (missing JSON)")
        return False

    if not original_path:
        log_progress("crop_specimens", current, total, f"Skipped {base_name} (missing original)")
        return False
        
    # Check if already processed
    if os.path.exists(specimen_folder) and any(os.path.isfile(os.path.join(specimen_folder, f)) for f in os.listdir(specimen_folder)):
        log_progress("crop_specimens", current, total, f"Skipped {base_name} (already processed)")
        return False

    os.makedirs(specimen_folder, exist_ok=True)
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            annotations = data.get('predictions', [])
            resized_dimensions = data.get('image', {})
            if not all(key in resized_dimensions for key in ['width', 'height']):
                log(f"Skipped {base_name}: Missing image dimensions in JSON")
                return False
    
        # Organize specimens by row for consistent numbering
        row_threshold = 50
        sorted_annotations = []
        current_row = []
        last_y = None
        
        for ann in sorted(annotations, key=lambda a: (a['y'], a['x'])):
            if last_y is None or abs(ann['y'] - last_y) > row_threshold:
                if current_row:
                    sorted_annotations.extend(sorted(current_row, key=lambda a: a['x']))
                current_row = [ann]
                last_y = ann['y']
            else:
                current_row.append(ann)
        if current_row:
            sorted_annotations.extend(sorted(current_row, key=lambda a: a['x']))
        
        with Image.open(original_path) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGB')
                
            scale_x = img.width / float(resized_dimensions['width'])
            scale_y = img.height / float(resized_dimensions['height'])
            
            for idx, ann in enumerate(sorted_annotations, 1):
                x, y = ann['x'], ann['y']
                width, height = ann['width'], ann['height']
                
                # Add padding around specimen
                padding = 10
                xmin = max(int((x - width/2 - padding) * scale_x), 0)
                ymin = max(int((y - height/2 - padding) * scale_y), 0)
                xmax = min(int((x + width/2 + padding) * scale_x), img.width)
                ymax = min(int((y + height/2 + padding) * scale_y), img.height)
                
                if xmax <= xmin or ymax <= ymin:
                    continue
                
                cropped = img.crop((xmin, ymin, xmax, ymax))
                output_path = os.path.join(
                    specimen_folder, 
                    f'{drawer_name}_tray_{tray_num}_spec_{idx:03}{original_ext}'
                )
                cropped.save(output_path)
        
        log_progress("crop_specimens", current, total, f"Processed {base_name} with {len(sorted_annotations)} specimens")
        return True
            
    except Exception as e:
        log(f"Error processing {base_name}: {str(e)}")
        return False

def find_processed_trays(specimens_dir):
    """Find all trays that have already been processed by looking for specimen images."""
    processed = set()
    for root, _, files in os.walk(specimens_dir):
        for file in files:
            if file.endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png')):
                # Extract tray identifier from specimen filename
                # Example: if file is "drawer_123_tray_01_spec_003.jpg"
                # We want "drawer_123_tray_01" as the tray identifier
                parts = file.split('_spec_')[0]  # Get everything before "_spec_"
                processed.add(parts)
    return processed

def crop_specimens_from_trays(trays_dir, resized_trays_dir, specimens_dir):
    """
    Crop individual specimens from tray images based on detected coordinates.
    """
    # Ensure output directory exists
    os.makedirs(specimens_dir, exist_ok=True)
    
    # Find all resized tray images
    resized_files = []
    for root, _, files in os.walk(resized_trays_dir):
        for f in files:
            if f.endswith('_1000.jpg'):
                resized_files.append((root, f))
    
    if not resized_files:
        log("No resized tray images found to process")
        return
        
    log_found("trays", len(resized_files))
    
    # Find already processed trays
    processed_trays = find_processed_trays(specimens_dir)
    if processed_trays:
        log(f"Found {len(processed_trays)} previously processed trays")
    
    # Prepare tasks, skipping already processed trays
    tasks = []
    for i, (root, f) in enumerate(resized_files, 1):
        base_name = f.replace('_1000.jpg', '')
        if base_name in processed_trays:
            continue
        tasks.append((trays_dir, resized_trays_dir, specimens_dir, root, f, i, len(resized_files)))
    
    if not tasks:
        log("All trays already processed")
        return
        
    log(f"Processing {len(tasks)} new trays")
    
    # Process in parallel
    num_workers = min(cpu_count(), len(tasks))
    with Pool(num_workers) as pool:
        results = pool.map(process_tray, tasks)
    
    # Count results
    processed = sum(1 for r in results if r)
    skipped = len(tasks) - processed
    
    log(f"Complete. {processed} processed, {skipped} skipped")




