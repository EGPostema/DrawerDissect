import os
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
from logging_utils import log, log_found, log_progress

def process_masking(args):
    """
    Apply a mask to a specimen image, replacing the background with white.
    
    Returns:
        bool: True if processed successfully, False if skipped
    """
    specimen_path, mask_path, output_path, current, total = args
    
    # Skip if already processed
    if os.path.exists(output_path):
        log_progress("censor_background", current, total, f"Skipped (already exists)")
        return False
    
    try:
        # Open and process the specimen image
        specimen_img = Image.open(specimen_path)
        if specimen_img.mode in ('RGBA', 'LA') or (specimen_img.mode == 'P' and 'transparency' in specimen_img.info):
            specimen_img = specimen_img.convert('RGB')
        
        # Open and process the mask
        mask_img = Image.open(mask_path).convert('L')
        
        # Ensure mask and specimen are the same size
        if specimen_img.size != mask_img.size:
            mask_img = mask_img.resize(specimen_img.size, Image.Resampling.NEAREST)
        
        # Convert to numpy arrays for processing
        specimen_np = np.array(specimen_img)
        mask_np = np.array(mask_img) / 255.0
        
        # Limit specimen pixels to range 1-254 to avoid overlap with background/mask values
        specimen_np = np.clip(specimen_np, 1, 254)
        
        background_img = np.ones_like(specimen_np) * 255  # White background
        
        # Apply the mask
        result_np = (specimen_np * np.stack([mask_np] * 3, axis=-1) +
                    background_img * (1 - np.stack([mask_np] * 3, axis=-1))).astype(np.uint8)
        
        # Save the result
        Image.fromarray(result_np).save(output_path)
        log_progress("censor_background", current, total, f"Processed {os.path.basename(specimen_path)}")
        return True
        
    except Exception as e:
        log(f"Error processing {os.path.basename(specimen_path)}: {str(e)}")
        return False

def find_mask_path(specimen_path, mask_dir):
    """Find the corresponding mask for a specimen image."""
    # Extract full_id from specimen path
    base_name = os.path.splitext(os.path.basename(specimen_path))[0]
    
    # Extract drawer and tray ids from the specimen path
    path_parts = os.path.normpath(specimen_path).split(os.sep)
    if len(path_parts) < 3:
        return None
        
    drawer_id = path_parts[-3]  # Three levels up for drawer
    tray_id = path_parts[-2]    # Two levels up for tray
    
    # Construct mask path
    mask_path = os.path.join(mask_dir, tray_id, f"{base_name}.png")
    
    return mask_path if os.path.exists(mask_path) else None

def censor_background(specimens_dir, mask_dir, masked_specs_dir):
    """
    Apply masks to specimen images to replace backgrounds with white.
    
    Args:
        specimens_dir: Directory containing specimen images
        mask_dir: Directory containing mask files (.png)
        masked_specs_dir: Directory to save processed images
    """
    # Create output directory if it doesn't exist
    os.makedirs(masked_specs_dir, exist_ok=True)
    
    # Find all specimen images that need processing
    tasks = []
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    
    for root, _, files in os.walk(specimens_dir):
        for file in files:
            if not file.lower().endswith(supported_formats):
                continue
                
            specimen_path = os.path.join(root, file)
            mask_path = find_mask_path(specimen_path, mask_dir)
            
            if not mask_path:
                continue
                
            # Create output path with the same folder structure
            relative_path = os.path.relpath(specimen_path, specimens_dir)
            output_path = os.path.join(masked_specs_dir, os.path.splitext(relative_path)[0] + '_masked' + os.path.splitext(file)[1])
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            tasks.append((specimen_path, mask_path, output_path))
    
    if not tasks:
        log("No valid specimen-mask pairs found to process")
        return
        
    log_found("specimen-mask pairs", len(tasks))
    
    # Count existing files that can be skipped
    existing = sum(1 for _, _, output_path in tasks if os.path.exists(output_path))
    if existing > 0:
        log(f"Found {existing} already processed images")
    
    # Add progress tracking indices
    tasks = [(t[0], t[1], t[2], i+1, len(tasks)) for i, t in enumerate(tasks)]
    
    # Process the images in parallel
    processed = 0
    skipped = 0
    
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_masking, tasks))
        
    for result in results:
        if result:
            processed += 1
        else:
            skipped += 1


