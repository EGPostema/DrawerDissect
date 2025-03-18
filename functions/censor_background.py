import os
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor

def process_masking(args):
    specimen_path, mask_path, output_path = args
    
    # Open and process the specimen image
    specimen_img = Image.open(specimen_path)
    if specimen_img.mode in ('RGBA', 'LA') or (specimen_img.mode == 'P' and 'transparency' in specimen_img.info):
        specimen_img = specimen_img.convert('RGB')
    
    # Open and process the mask
    mask_img = Image.open(mask_path).convert('L')
    
    # Convert to numpy arrays for processing
    specimen_np = np.array(specimen_img)
    mask_np = np.array(mask_img) / 255.0
    background_img = np.ones_like(specimen_np) * 255  # White background
    
    # Apply the mask
    result_np = (specimen_np * np.stack([mask_np] * 3, axis=-1) +
                background_img * (1 - np.stack([mask_np] * 3, axis=-1))).astype(np.uint8)
    
    # Save the result
    Image.fromarray(result_np).save(output_path)
    return f"Processed {os.path.basename(specimen_path)}"

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
    
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    tasks = []
    
    # Walk through the specimens directory
    for root, _, files in os.walk(specimens_dir):
        for file in files:
            if file.lower().endswith(supported_formats):
                specimen_path = os.path.join(root, file)
                relative_path = os.path.relpath(specimen_path, specimens_dir)
                original_ext = os.path.splitext(file)[1]
                
                mask_path = os.path.join(mask_dir, os.path.splitext(relative_path)[0] + '.png')
                output_path = os.path.join(masked_specs_dir, os.path.splitext(relative_path)[0] + '_masked' + original_ext)
                output_dir = os.path.dirname(output_path)
                os.makedirs(output_dir, exist_ok=True)
                
                # Process the specimen if:
                # 1. The mask exists
                # 2. The output doesn't already exist
                if os.path.exists(mask_path) and not os.path.exists(output_path):
                    tasks.append((specimen_path, mask_path, output_path))
                else:
                    if not os.path.exists(mask_path):
                        print(f"Skipping {file}: No mask found at {mask_path}")
                    elif os.path.exists(output_path):
                        print(f"Skipping {file}: Already processed")
    
    print(f"Processing {len(tasks)} images...")
    
    # Process the tasks in parallel
    with ProcessPoolExecutor() as executor:
        for result in executor.map(process_masking, tasks):
            print(result)


