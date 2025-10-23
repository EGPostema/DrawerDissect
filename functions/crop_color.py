import os
import json
from PIL import Image, ImageFile
from multiprocessing import Pool, cpu_count
from logging_utils import log, log_found, log_progress
from config import DrawerDissectConfig

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def crop_color_from_fullsize(fullsize_dir, resized_dir, output_dir, sequential=False, max_workers=None, batch_size=None):
    """
    Crop color standards from full-size drawer images using coordinates from resized images.
    
    Args:
        fullsize_dir: Directory containing original full-size drawer images
        resized_dir: Directory containing resized images and color_coordinates subdirectory
        output_dir: Directory to save cropped color standard images
        sequential: If True, process images one at a time
        max_workers: Maximum number of parallel workers (None = auto)
        batch_size: Process images in batches of this size (None = all at once)
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Get coordinate files
    coords_dir = os.path.join(resized_dir, 'color_coordinates')
    if not os.path.exists(coords_dir):
        log(f"Error: Coordinates directory not found: {coords_dir}")
        return
    
    coord_files = [f for f in os.listdir(coords_dir) if f.endswith('_color.json')]
    total_files = len(coord_files)
    log_found("coordinate files", total_files)
    
    if total_files == 0:
        log("No coordinate files found to process")
        return
    
    # Prepare tasks
    tasks = []
    for coord_file in coord_files:
        # Get base filename: remove _1000_color.json to get the original base name
        # FMNH_cicindelidae_34_5_7_1000_color.json -> FMNH_cicindelidae_34_5_7
        base_name = coord_file.replace('_1000_color.json', '')
        
        # Find corresponding full-size image
        fullsize_path = None
        for ext in ['.jpg', '.jpeg', '.tif', '.tiff', '.png']:
            potential_path = os.path.join(fullsize_dir, base_name + ext)
            if os.path.exists(potential_path):
                fullsize_path = potential_path
                break
        
        if not fullsize_path:
            log(f"Warning: No full-size image found for {base_name}")
            continue
        
        # Find corresponding resized image
        resized_path = os.path.join(resized_dir, base_name + '_1000.jpg')
        if not os.path.exists(resized_path):
            log(f"Warning: No resized image found for {base_name}")
            continue
        
        coord_path = os.path.join(coords_dir, coord_file)
        tasks.append((fullsize_path, resized_path, coord_path, output_dir, base_name))
    
    if not tasks:
        log("No valid image pairs found to process")
        return
    
    log(f"Processing {len(tasks)} drawer images")
    
    # Process based on settings
    if sequential:
        log("Processing sequentially (one at a time)")
        for i, task in enumerate(tasks, 1):
            result = process_single_color_crop(task)
            if result:
                log_progress("crop_color", i, len(tasks), f"Cropped {result} color standards")
    else:
        workers = max_workers if max_workers else cpu_count()
        log(f"Processing in parallel with {workers} workers")
        
        with Pool(processes=workers) as pool:
            if batch_size:
                log(f"Processing in batches of {batch_size}")
                for i in range(0, len(tasks), batch_size):
                    batch = tasks[i:i + batch_size]
                    results = pool.map(process_single_color_crop, batch)
                    for j, result in enumerate(results, 1):
                        progress = i + j
                        if result:
                            log_progress("crop_color", progress, len(tasks), 
                                       f"Cropped {result} color standards")
            else:
                results = pool.map(process_single_color_crop, tasks)
                for i, result in enumerate(results, 1):
                    if result:
                        log_progress("crop_color", i, len(tasks), 
                                   f"Cropped {result} color standards")

def process_single_color_crop(task):
    """
    Process a single drawer image to crop color standards.
    
    Args:
        task: Tuple of (fullsize_path, resized_path, coord_path, output_dir, base_name)
    
    Returns:
        Number of color standards cropped, or None if error
    """
    fullsize_path, resized_path, coord_path, output_dir, base_name = task
    
    try:
        # Load coordinates
        with open(coord_path, 'r') as f:
            coord_data = json.load(f)
        
        predictions = coord_data.get('predictions', [])
        if not predictions:
            return 0
        
        # Get the file extension from the original full-size image
        original_ext = os.path.splitext(fullsize_path)[1]
        
        # Check if all expected outputs already exist
        all_exist = True
        for prediction in predictions:
            class_name = prediction.get('class', 'unknown')
            output_filename = f"{base_name}_{class_name}{original_ext}"
            output_path = os.path.join(output_dir, output_filename)
            if not os.path.exists(output_path):
                all_exist = False
                break
        
        # Skip if all outputs already exist
        if all_exist:
            return 0  # Return 0 to indicate skipped (already processed)
        
        # Open images
        fullsize_img = Image.open(fullsize_path)
        resized_img = Image.open(resized_path)
        
        # Calculate scaling factors
        scale_x = fullsize_img.width / resized_img.width
        scale_y = fullsize_img.height / resized_img.height
        
        # Crop each detected color standard
        cropped_count = 0
        for prediction in predictions:
            # Get class name
            class_name = prediction.get('class', 'unknown')
            
            # Check if this specific output already exists
            output_filename = f"{base_name}_{class_name}{original_ext}"
            output_path = os.path.join(output_dir, output_filename)
            
            if os.path.exists(output_path):
                continue  # Skip this one, it's already been cropped
            
            # Get bounding box from resized image coordinates
            x_center = prediction['x']
            y_center = prediction['y']
            width = prediction['width']
            height = prediction['height']
            
            # Convert to corner coordinates
            x1 = x_center - (width / 2)
            y1 = y_center - (height / 2)
            x2 = x_center + (width / 2)
            y2 = y_center + (height / 2)
            
            # Scale to full-size image coordinates
            x1_full = int(x1 * scale_x)
            y1_full = int(y1 * scale_y)
            x2_full = int(x2 * scale_x)
            y2_full = int(y2 * scale_y)
            
            # Ensure coordinates are within image bounds
            x1_full = max(0, x1_full)
            y1_full = max(0, y1_full)
            x2_full = min(fullsize_img.width, x2_full)
            y2_full = min(fullsize_img.height, y2_full)
            
            # Crop the color standard
            color_crop = fullsize_img.crop((x1_full, y1_full, x2_full, y2_full))
            
            # Save in the same format as input
            color_crop.save(output_path)
            
            cropped_count += 1
        
        fullsize_img.close()
        resized_img.close()
        
        return cropped_count
        
    except Exception as e:
        log(f"Error processing {base_name}: {str(e)}")
        return None