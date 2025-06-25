import os
import json
import shutil
from PIL import Image, ImageDraw
from concurrent.futures import ProcessPoolExecutor
from logging_utils import log, log_found, log_progress

def process_mask(args):
    """
    Process a specimen mask and corresponding pin JSON file to create a combined mask.
    
    Returns:
        str: Status message
    """
    image_path, json_path, output_dir, base_name, current, total = args
    
    # First check if any version of the output already exists
    existing_files = [
        os.path.join(output_dir, f"{base_name}_fullmask.png"),
        os.path.join(output_dir, f"{base_name}_fullmask_unedited.png")
    ]
    # Also check for numbered masks (up to a reasonable number)
    for i in range(1, 10):  # Assuming no more than 9 pins
        existing_files.append(os.path.join(output_dir, f"{base_name}_fullmask_{i}.png"))
        
    if any(os.path.exists(f) for f in existing_files):
        log_progress("create_pinmask", current, total, f"Skipped (already exists)")
        return False
    
    try:
        with Image.open(image_path).convert("RGB") as mask_image:
            if json_path and os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                pin_count = 0
                pin_polygons = []
                
                # Extract pin polygons from JSON
                for pred in data.get('predictions', []):
                    if pred['class'] == 'pin':
                        points = [(point['x'], point['y']) for point in pred['points']]
                        pin_polygons.append(points)
                        pin_count += 1
                
                if pin_count > 1:
                    # Create separate masks for each pin
                    for i, points in enumerate(pin_polygons, start=1):
                        separate_mask = mask_image.copy()
                        draw = ImageDraw.Draw(separate_mask)
                        draw.polygon(points, fill="black")
                        separate_output_path = os.path.join(output_dir, f"{base_name}_fullmask_{i}.png")
                        separate_mask.save(separate_output_path)
                    
                    log_progress("create_pinmask", current, total, f"Created {pin_count} pin masks")
                    return True
                    
                elif pin_count == 1:
                    # Single pin, create one mask
                    draw = ImageDraw.Draw(mask_image)
                    draw.polygon(pin_polygons[0], fill="black")
                    output_path = os.path.join(output_dir, f"{base_name}_fullmask.png")
                    mask_image.save(output_path)
                    
                    log_progress("create_pinmask", current, total, f"Created 1 pin mask")
                    return True
                    
                else:
                    # No pins found, copy original image as unedited
                    output_path = os.path.join(output_dir, f"{base_name}_fullmask_unedited.png")
                    shutil.copy(image_path, output_path)
                    
                    log_progress("create_pinmask", current, total, f"No pins found")
                    return True
                    
            else:
                # No JSON file found, copy original image as unedited
                output_path = os.path.join(output_dir, f"{base_name}_fullmask_unedited.png")
                shutil.copy(image_path, output_path)
                
                log_progress("create_pinmask", current, total, f"No JSON data")
                return True
                
    except Exception as e:
        log(f"Error creating pin mask for {base_name}: {str(e)}")
        return False

def create_pinmask(image_input_dir, coord_input_dir, output_dir):
    """
    Create pin masks from specimen masks and pin segmentation data.
    
    Args:
        image_input_dir: Directory containing specimen mask images
        coord_input_dir: Directory containing pin segmentation JSON files
        output_dir: Directory to save the combined masks
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all mask images and corresponding JSON files
    tasks = []
    
    for root, _, files in os.walk(image_input_dir):
        for file in files:
            if not file.endswith('.png'):
                continue
                
            # Get the specimen ID and paths
            full_id = file.replace('.png', '')
            image_path = os.path.join(root, file)
            rel_path = os.path.relpath(root, image_input_dir)
            
            # Find the corresponding JSON file
            json_path = os.path.join(coord_input_dir, rel_path, f"{full_id}_masked.json")
            
            # Create output directory with the same structure
            out_subfolder = os.path.join(output_dir, rel_path)
            os.makedirs(out_subfolder, exist_ok=True)
            
            tasks.append((image_path, json_path, out_subfolder, full_id))
    
    if not tasks:
        log("No mask files found to process")
        return
        
    log_found("mask files", len(tasks))
    
    # Add progress tracking indices
    tasks = [(t[0], t[1], t[2], t[3], i+1, len(tasks)) for i, t in enumerate(tasks)]
    
    # Process masks in parallel
    processed = 0
    skipped = 0
    
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_mask, tasks))


