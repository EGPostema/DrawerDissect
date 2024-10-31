import os
from PIL import Image
import numpy as np
from concurrent.futures import ProcessPoolExecutor

def mask_specimens(specimens_dir, mask_dir, masked_specs_dir, background):
    tasks = []
    
    # Prepare all the image paths
    for root, dirs, files in os.walk(specimens_dir):
        for filename in files:
            if filename.endswith('.jpg'):
                # Get relative path to preserve subfolder structure
                relative_path = os.path.relpath(root, specimens_dir)
                specimen_path = os.path.join(root, filename)

                # Find corresponding mask image in mask_dir, preserving the subfolder structure
                mask_path = os.path.join(mask_dir, relative_path, filename.replace('.jpg', '.png'))

                # Create the corresponding output directory in masked_specs_dir
                output_dir = os.path.join(masked_specs_dir, relative_path)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                output_path = os.path.join(output_dir, filename.replace('.jpg', '_masked.png'))

                # Check if the masked image already exists
                if not os.path.exists(output_path):
                    if os.path.exists(mask_path):
                        tasks.append((specimen_path, mask_path, output_path, background))
                    else:
                        print(f"Mask not found for {specimen_path}")
                else:
                    print(f"Masked specimen already exists for {filename}, skipping.")

    # Use multiprocessing to handle the masking tasks
    with ProcessPoolExecutor() as executor:
        executor.map(process_masking, tasks)

def process_masking(task):
    specimen_path, mask_path, output_path, background = task
    mask_specimen(specimen_path, mask_path, output_path, background)

def mask_specimen(specimen_path, mask_path, output_path, background):
    # Load the specimen image and the mask
    specimen_img = Image.open(specimen_path)
    mask_img = Image.open(mask_path).convert('L')  # Convert mask to grayscale
    
    # Convert both images to NumPy arrays
    specimen_np = np.array(specimen_img)
    mask_np = np.array(mask_img)
    
    # Normalize mask to have values between 0 and 1
    mask_np = mask_np / 255.0
    
    if background == 'white':
        # Create a white background
        background_img = np.ones_like(specimen_np) * 255
    else:
        # Create a black background
        background_img = np.zeros_like(specimen_np)
    
    # Combine the specimen with the background using the mask
    result_np = (specimen_np * np.stack([mask_np, mask_np, mask_np], axis=-1) +
                 background_img * (1 - np.stack([mask_np, mask_np, mask_np], axis=-1))).astype(np.uint8)
    
    # Convert the result back to an image
    result_img = Image.fromarray(result_np)
    
    # Save the result
    result_img.save(output_path)
    print(f"Masked specimen saved to {output_path}")
