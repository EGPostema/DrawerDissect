import os
import pandas as pd
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor

def process_masking(args):
    specimen_path, mask_path, output_path = args  # Only unpack three arguments
    specimen_img = Image.open(specimen_path)
    mask_img = Image.open(mask_path).convert('L')
    
    specimen_np = np.array(specimen_img)
    mask_np = np.array(mask_img) / 255.0
    background_img = np.ones_like(specimen_np) * 255  # White background
    
    # Create censored image
    result_np = (specimen_np * np.stack([mask_np] * 3, axis=-1) +
                 background_img * (1 - np.stack([mask_np] * 3, axis=-1))).astype(np.uint8)
    
    # Save the output
    Image.fromarray(result_np).save(output_path)
    return f"Processed {os.path.basename(specimen_path)}"

def censor_background(specimens_dir, mask_dir, masked_specs_dir, measurements_csv):
    # Read measurements CSV and filter valid rows
    df = pd.read_csv(measurements_csv)
    valid_specimens = df[
        (df['mask_OK'] == 'Y') &  
        (df['bad_size'] == 'N')
    ]['full_id'].tolist()
    
    valid_specimen_set = set(valid_specimens)  # For quick lookup

    tasks = []
    for root, _, files in os.walk(specimens_dir):
        for file in files:
            if file.endswith(".jpg"):
                # Extract the full_id from the filename (remove .jpg)
                full_id = os.path.splitext(file)[0]

                # Build paths for specimen and mask
                specimen_path = os.path.join(root, file)
                relative_path = os.path.relpath(specimen_path, specimens_dir)
                mask_path = os.path.join(mask_dir, relative_path.replace(".jpg", ".png"))

                # Ensure the output directory mirrors the input structure
                output_path = os.path.join(masked_specs_dir, relative_path.replace(".jpg", "_masked.png"))
                output_dir = os.path.dirname(output_path)
                os.makedirs(output_dir, exist_ok=True)

                # Check if the full_id is valid and if the mask exists
                if (full_id in valid_specimen_set and
                        os.path.exists(mask_path) and
                        not os.path.exists(output_path)):
                    tasks.append((specimen_path, mask_path, output_path))
                else:
                    print(f"Skipping {file}: Missing mask or already processed.")
    
    # Use multiprocessing to process the tasks
    with ProcessPoolExecutor() as executor:
        for result in executor.map(process_masking, tasks):
            print(result)


