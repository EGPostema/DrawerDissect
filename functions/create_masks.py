import os
import json
from PIL import Image, ImageDraw
from concurrent.futures import ThreadPoolExecutor
from logging_utils import log, log_found, log_progress

def process_mask(args):
    """
    Create a binary mask from a segmentation JSON file.
    
    Returns:
        bool: True if processed successfully, False otherwise
    """
    json_path, png_path, current, total = args
    
    # Skip if mask already exists
    if os.path.exists(png_path):
        log_progress("create_masks", current, total, f"Skipped (already exists)")
        return False
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        image_info = data.get('image', {})
        img_width = int(image_info.get('width', 0))
        img_height = int(image_info.get('height', 0))
        
        if not (img_width and img_height):
            log(f"Skipped {json_path}: Invalid dimensions")
            return False
            
        binary_mask = Image.new('L', (img_width, img_height))
        draw = ImageDraw.Draw(binary_mask)
        
        for prediction in data.get('predictions', []):
            points = prediction.get('points', [])
            if not points:
                continue
                
            xy = [(int(point['x']), int(point['y'])) for point in points]
            draw.polygon(xy, outline=0, fill=255)
        
        binary_mask.save(png_path, optimize=True)
        log_progress("create_masks", current, total, f"Created mask")
        return True
        
    except Exception as e:
        log(f"Error with {os.path.basename(json_path)}: {str(e)}")
        return False

def create_masks(jsondir, pngdir):
    """
    Create binary masks from segmentation JSON files.
    Handles both tray-based and specimen-only directory structures.
    
    Args:
        jsondir: Directory containing segmentation JSON files
        pngdir: Directory to save binary mask PNG files
    """
    # Ensure output directory exists
    os.makedirs(pngdir, exist_ok=True)
    
    # Find all JSON files that need processing
    tasks = []
    for root, _, files in os.walk(jsondir):
        json_files = [f for f in files if f.endswith('.json')]
        if not json_files:
            continue
            
        rel_dir = os.path.relpath(root, jsondir)
        
        for file in json_files:
            json_path = os.path.join(root, file)
            
            # Create output structure that mirrors input
            if rel_dir == '.':
                # Files are in the root of jsondir - put masks in root of pngdir
                png_subfolder = pngdir
            else:
                # Files are in subdirectories - mirror the structure
                png_subfolder = os.path.join(pngdir, rel_dir)
            
            os.makedirs(png_subfolder, exist_ok=True)
            png_path = os.path.join(png_subfolder, file.replace('.json', '.png'))
            tasks.append((json_path, png_path))
    
    if not tasks:
        log("No JSON files found to process")
        return
        
    log_found("segmentation files", len(tasks))
    
    # Add progress tracking indices
    tasks = [(t[0], t[1], i+1, len(tasks)) for i, t in enumerate(tasks)]
    
    # Process masks in parallel
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda x: process_mask(x), tasks))
