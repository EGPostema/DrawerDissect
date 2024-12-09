import os
import time
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
import logging
from typing import Tuple, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_single_image(args: Tuple[str, str, str]) -> bool:
    specimen_path, mask_path, output_path = args
    
    if os.path.exists(output_path):
        return False
        
    try:
        with Image.open(specimen_path).convert("RGBA") as specimen_image:
            with Image.open(mask_path).convert("L") as mask_image:
                if specimen_image.size != mask_image.size:
                    mask_image = mask_image.resize(specimen_image.size, Image.Resampling.LANCZOS)
                
                r, g, b, _ = specimen_image.split()
                transparent_image = Image.merge('RGBA', (r, g, b, mask_image))
                transparent_image.save(output_path, "PNG", optimize=True)
                transparent_image.close()
                return True
                
    except Exception as e:
        logger.error(f"Error processing {specimen_path}: {str(e)}")
        return False

def find_mask_path(specimen_path: str, mask_dir: str) -> str:
    path_parts = os.path.normpath(specimen_path).split(os.sep)
    if len(path_parts) < 4:
        return ""
        
    drawer_id = path_parts[-3]
    tray_id = path_parts[-2]
    specimen_name = os.path.splitext(path_parts[-1])[0]
    
    mask_subdir = os.path.join(mask_dir, drawer_id, tray_id)
    mask_options = [f"{specimen_name}_fullmask.png", f"{specimen_name}_fullmask_unedited.png"]
    
    for mask_name in mask_options:
        mask_path = os.path.join(mask_subdir, mask_name)
        if os.path.exists(mask_path):
            return mask_path
    return ""

def create_transparency(specimen_input_dir: str, mask_input_dir: str, output_dir: str) -> None:
    start_time = time.time()
    tasks: List[Tuple[str, str, str]] = []

    for root, _, files in os.walk(specimen_input_dir):
        for file in (f for f in files if f.lower().endswith(('.jpg', '.png'))):
            specimen_path = os.path.join(root, file)
            mask_path = find_mask_path(specimen_path, mask_input_dir)
            
            if not mask_path:
                continue
                
            relative_path = os.path.relpath(root, specimen_input_dir)
            output_subfolder = os.path.join(output_dir, relative_path)
            os.makedirs(output_subfolder, exist_ok=True)
            
            output_path = os.path.join(
                output_subfolder,
                f"{os.path.splitext(file)[0]}_finalmask.png"
            )
            tasks.append((specimen_path, mask_path, output_path))

    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_single_image, tasks))
    
    elapsed = time.time() - start_time
    processed = sum(1 for r in results if r)
    errors = sum(1 for r in results if not r)
    avg_time = elapsed / len(tasks) if tasks else 0
    
    logger.info(f"Complete: {processed} processed, {errors} errors, {elapsed:.1f}s total, {avg_time:.1f}s/image")

