import os
import pandas as pd
import numpy as np
from PIL import Image
from concurrent.futures import ProcessPoolExecutor

def process_masking(args):
    specimen_path, mask_path, output_path = args
    specimen_img = Image.open(specimen_path)
    if specimen_img.mode in ('RGBA', 'LA') or (specimen_img.mode == 'P' and 'transparency' in specimen_img.info):
        specimen_img = specimen_img.convert('RGB')
    mask_img = Image.open(mask_path).convert('L')
    
    specimen_np = np.array(specimen_img)
    mask_np = np.array(mask_img) / 255.0
    background_img = np.ones_like(specimen_np) * 255
    
    result_np = (specimen_np * np.stack([mask_np] * 3, axis=-1) +
                background_img * (1 - np.stack([mask_np] * 3, axis=-1))).astype(np.uint8)
    
    Image.fromarray(result_np).save(output_path)
    return f"Processed {os.path.basename(specimen_path)}"

def censor_background(specimens_dir, mask_dir, masked_specs_dir, measurements_csv):
    df = pd.read_csv(measurements_csv)
    valid_specimens = df[
        (df['mask_OK'] == 'Y') &  
        (df['bad_size'] == 'N')
    ]['full_id'].tolist()
    
    valid_specimen_set = set(valid_specimens)
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')

    tasks = []
    for root, _, files in os.walk(specimens_dir):
        for file in files:
            if file.lower().endswith(supported_formats):
                full_id = os.path.splitext(file)[0]
                specimen_path = os.path.join(root, file)
                relative_path = os.path.relpath(specimen_path, specimens_dir)
                original_ext = os.path.splitext(file)[1]
                
                mask_path = os.path.join(mask_dir, os.path.splitext(relative_path)[0] + '.png')
                output_path = os.path.join(masked_specs_dir, os.path.splitext(relative_path)[0] + '_masked' + original_ext)
                output_dir = os.path.dirname(output_path)
                os.makedirs(output_dir, exist_ok=True)

                if (full_id in valid_specimen_set and
                        os.path.exists(mask_path) and
                        not os.path.exists(output_path)):
                    tasks.append((specimen_path, mask_path, output_path))
                else:
                    print(f"Skipping {file}: Missing mask or already processed.")
    
    with ProcessPoolExecutor() as executor:
        for result in executor.map(process_masking, tasks):
            print(result)


