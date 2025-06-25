import os
import json
import re
from PIL import Image, ImageFile
from concurrent.futures import ThreadPoolExecutor
from logging_utils import log, log_found, log_progress

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def process_label(args):
    fullsize_dir, resized_dir, coordinates_dir, output_dir, root, resized_filename, current, total = args
    
    base_name_1000 = resized_filename.replace('.jpg', '')
    base_name = base_name_1000.replace('_1000', '')
    json_filename = f"{base_name_1000}_label.json"
    
    # Extract drawer_name and tray_num using regex for better reliability
    match = re.search(r'(.+)_tray_(\d+)$', base_name)
    if match:
        drawer_name = match.group(1)
        tray_num = match.group(2)
    else:
        # Fallback to old method if regex doesn't match
        drawer_name = '_'.join(base_name.split('_')[:-2])
        tray_num = base_name.split('_')[-1]
    
    # Get relative path from resized directory
    relative_path = os.path.relpath(root, resized_dir)
    if relative_path == '.':
        relative_path = ''
    
    # Find original file with any supported extension
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    original_path = None
    original_ext = None
    
    # Try multiple paths to find the original image
    search_paths = [
        # Standard path with drawer_name
        os.path.join(fullsize_dir, drawer_name, f"{base_name}"),
        # Try with relative path if it's different from drawer_name
        os.path.join(fullsize_dir, relative_path, f"{base_name}") if relative_path and relative_path != drawer_name else None,
        # Try with direct folder path if it contains drawer_name
        os.path.join(fullsize_dir, drawer_name, f"{drawer_name}_tray_{tray_num}")
    ]
    
    # Filter out None values
    search_paths = [p for p in search_paths if p]
    
    # Try each potential path
    for search_path in search_paths:
        for ext in supported_formats:
            test_path = f"{search_path}{ext}"
            if os.path.exists(test_path):
                original_path = test_path
                original_ext = ext
                break
        if original_path:
            break
    
    # If still not found, search recursively
    if not original_path:
        for root_dir, _, files in os.walk(fullsize_dir):
            for file in files:
                file_base, file_ext = os.path.splitext(file)
                if (file_base == base_name or file_base == f"{drawer_name}_tray_{tray_num}") and file_ext.lower() in supported_formats:
                    original_path = os.path.join(root_dir, file)
                    original_ext = file_ext
                    break
            if original_path:
                break
    
    # Search recursively for the JSON file
    json_files = []
    for root_dir, _, files in os.walk(coordinates_dir):
        for file in files:
            if file == json_filename:
                json_path = os.path.join(root_dir, file)
                json_files.append(json_path)
    
    # Use the first JSON file found, if any
    json_path = json_files[0] if json_files else None
    
    # Create output directory that preserves structure
    output_folder = os.path.join(output_dir, tray_num)
    
    if not original_path:
        log_progress("crop_labels", current, total, f"Skipped {base_name} (missing original)")
        return False
        
    if not json_path:
        log_progress("crop_labels", current, total, f"Skipped {base_name} (missing JSON)")
        return False

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            if not data.get('predictions'):
                log_progress("crop_labels", current, total, f"Skipped {base_name} (no predictions)")
                return False

        os.makedirs(output_folder, exist_ok=True)
        
        # Check if any label has already been processed
        any_label_exists = any(
            os.path.exists(os.path.join(output_folder, f"{base_name}_{label_type}.jpg"))
            for label_type in ['barcode', 'geocode', 'label', 'qr']
        )
        
        if any_label_exists:
            log_progress("crop_labels", current, total, f"Skipped {base_name} (already processed)")
            return False
        
        with Image.open(original_path) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGB')
                
            scale_x = img.width / float(data['image']['width'])
            scale_y = img.height / float(data['image']['height'])
            
            processed = set()
            for pred in data['predictions']:
                class_name = pred['class']
                if class_name not in ['barcode', 'geocode', 'label', 'qr']:
                    continue
                
                output_path = os.path.join(output_folder, f"{base_name}_{class_name}.jpg")
                if os.path.exists(output_path):
                    processed.add(class_name)
                    continue
                    
                x, y = pred['x'], pred['y']
                width, height = pred['width'], pred['height']
                
                xmin = max(int((x - width/2) * scale_x), 0)
                ymin = max(int((y - height/2) * scale_y), 0)
                xmax = min(int((x + width/2) * scale_x), img.width)
                ymax = min(int((y + height/2) * scale_y), img.height)
                
                cropped = img.crop((xmin, ymin, xmax, ymax))
                cropped.save(output_path)
                processed.add(class_name)
            
            log_progress("crop_labels", current, total, f"Processed {base_name}")
            return True
            
    except Exception as e:
        log(f"Error processing {base_name}: {str(e)}")
        return False

def crop_labels(fullsize_dir, resized_dir, coordinates_dir, output_dir):
    """
    Crop label components from tray images based on detected coordinates.
    
    This function supports nested directory structures by:
    1. Finding all resized tray images (recursively)
    2. Locating original images using flexible path search
    3. Finding label JSONs with recursive search
    4. Preserving directory structure in outputs
    
    Args:
        fullsize_dir: Directory containing original tray images
        resized_dir: Directory containing resized tray images
        coordinates_dir: Directory containing label detection JSON files
        output_dir: Directory where cropped labels will be saved
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all tray images that need processing
    all_tasks = []
    for root, _, files in os.walk(resized_dir):
        resized_files = [f for f in files if f.endswith('_1000.jpg')]
        if not resized_files:
            continue
            
        # Add to task list
        for f in resized_files:
            all_tasks.append((fullsize_dir, resized_dir, coordinates_dir, output_dir, root, f))

    if not all_tasks:
        log("No images found to process")
        return
        
    # Add proper progress tracking indices
    tasks = [(t[0], t[1], t[2], t[3], t[4], t[5], i+1, len(all_tasks)) 
             for i, t in enumerate(all_tasks)]
    
    log_found("images", len(tasks))
    
    # Process the labels
    processed = 0
    skipped = 0
    
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda x: process_label(x), tasks))

