import os
import json
import time
from PIL import Image, ImageFile
from multiprocessing import Pool, cpu_count

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def process_tray(args):
    trays_dir, resized_trays_dir, specimens_dir, root, resized_filename = args
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
    
    if not os.path.exists(json_path) or not original_path:
        return f"Skipped {base_name}: Missing required files"

    os.makedirs(specimen_folder, exist_ok=True)
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            annotations = data.get('predictions', [])
            resized_dimensions = data.get('image', {})
            if not all(key in resized_dimensions for key in ['width', 'height']):
                return f"Skipped {base_name}: Missing image dimensions in JSON"
    
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
            
            return f"Processed {base_name}: Saved {len(sorted_annotations)} specimens"
            
    except Exception as e:
        return f"Failed {base_name}: {str(e)}"

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
    # First find all already processed trays
    processed_trays = find_processed_trays(specimens_dir)
    print(f"Found {len(processed_trays)} already processed trays")
    
    tasks = []
    for root, _, files in os.walk(resized_trays_dir):
        for f in files:
            if f.endswith('_1000.jpg'):
                base_name = f.replace('_1000.jpg', '')
                # If this tray has already been processed, skip it
                if base_name in processed_trays:
                    print(f"Skipping already processed tray: {base_name}")
                    continue
                tasks.append((trays_dir, resized_trays_dir, specimens_dir, root, f))

    print(f"Processing {len(tasks)} new trays")
    with Pool(cpu_count()) as pool:
        results = pool.map(process_tray, tasks)
    
    for result in results:
        print(result)




