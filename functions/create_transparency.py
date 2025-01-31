import os
import time
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
import logging
from typing import Tuple, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_mask(mask_path: str) -> bool:
    try:
        with Image.open(mask_path) as mask:
            mask_gray = mask.convert('L')
            values = set(mask_gray.getdata())
            filtered_values = {v for v in values if v > 5 and v < 250}
            if len(filtered_values) > 2:
                logger.warning(f"Mask {mask_path} has unexpected gray values: {filtered_values}")
                return False
            return True
    except Exception as e:
        logger.error(f"Error validating mask {mask_path}: {str(e)}")
        return False

def validate_image_pair(specimen_path: str, mask_path: str) -> bool:
    try:
        with Image.open(specimen_path) as specimen, Image.open(mask_path) as mask:
            spec_ratio = specimen.size[0] / specimen.size[1]
            mask_ratio = mask.size[0] / mask.size[1]
            if abs(spec_ratio - mask_ratio) > 0.01:
                logger.warning(f"Aspect ratio mismatch: {specimen_path} ({spec_ratio:.3f}) vs {mask_path} ({mask_ratio:.3f})")
                return False
            return True
    except Exception as e:
        logger.error(f"Error validating image pair: {str(e)}")
        return False

def process_single_image(args: Tuple[str, str, str, str]) -> bool:
    specimen_path, mask_path, transparent_output_path, whitebg_output_path = args
    
    if os.path.exists(transparent_output_path):
        return False
        
    try:
        with Image.open(specimen_path).convert("RGBA") as specimen_image:
            with Image.open(mask_path).convert("L") as mask_image:
                if specimen_image.size != mask_image.size:
                    logger.warning(f"Size mismatch for {specimen_path}. Resizing mask from {mask_image.size} to {specimen_image.size}")
                    mask_image = mask_image.resize(specimen_image.size, Image.Resampling.LANCZOS)
                
                enhanced_mask = mask_image.point(lambda x: 255 if x > 128 else 0)
                r, g, b, _ = specimen_image.split()
                alpha = enhanced_mask.point(lambda x: 255 if x > 128 else 0)
                
                # Create transparent version
                transparent_image = Image.merge('RGBA', (r, g, b, alpha))
                transparent_image.save(transparent_output_path, "PNG", optimize=True)
                
                # Create white background version
                white_bg = Image.new('RGB', specimen_image.size, (255, 255, 255))
                white_bg.paste(transparent_image, mask=alpha)
                white_bg.save(whitebg_output_path)
                
                return True
                
    except Exception as e:
        logger.error(f"Error processing {specimen_path}: {str(e)}")
        return False

def find_mask_path(specimen_path: str, mask_dir: str) -> Optional[str]:
    path_parts = os.path.normpath(specimen_path).split(os.sep)
    if len(path_parts) < 4:
        logger.warning(f"Invalid specimen path structure: {specimen_path}")
        return None
        
    drawer_id = path_parts[-3]
    tray_id = path_parts[-2]
    specimen_name = os.path.splitext(path_parts[-1])[0]
    
    mask_subdir = os.path.join(mask_dir, drawer_id, tray_id)
    mask_options = [f"{specimen_name}_fullmask.png", f"{specimen_name}_fullmask_unedited.png"]
    
    for mask_name in mask_options:
        mask_path = os.path.join(mask_subdir, mask_name)
        if os.path.exists(mask_path):
            return mask_path
            
    logger.warning(f"No mask found for specimen: {specimen_path}")
    return None

def create_transparency(specimen_input_dir: str, mask_input_dir: str, transparent_output_dir: str, whitebg_output_dir: str) -> None:
    start_time = time.time()
    tasks: List[Tuple[str, str, str, str]] = []
    skipped = 0
    invalid_masks = 0
    invalid_pairs = 0

    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    for root, _, files in os.walk(specimen_input_dir):
        for file in (f for f in files if f.lower().endswith(supported_formats)):
            specimen_path = os.path.join(root, file)
            mask_path = find_mask_path(specimen_path, mask_input_dir)
            
            if not mask_path:
                skipped += 1
                continue
                
            if not validate_mask(mask_path):
                logger.warning(f"Skipping invalid mask: {mask_path}")
                invalid_masks += 1
                continue
                
            if not validate_image_pair(specimen_path, mask_path):
                logger.warning(f"Skipping invalid image pair: {specimen_path}, {mask_path}")
                invalid_pairs += 1
                continue
                
            relative_path = os.path.relpath(root, specimen_input_dir)
            transparent_subfolder = os.path.join(transparent_output_dir, relative_path)
            whitebg_subfolder = os.path.join(whitebg_output_dir, relative_path)
            os.makedirs(transparent_subfolder, exist_ok=True)
            os.makedirs(whitebg_subfolder, exist_ok=True)
            
            original_ext = os.path.splitext(file)[1]
            base_name = os.path.splitext(file)[0]
            
            transparent_output_path = os.path.join(transparent_subfolder, f"{base_name}_finalmask.png")
            whitebg_output_path = os.path.join(whitebg_subfolder, f"{base_name}_whitebg{original_ext}")
            
            tasks.append((specimen_path, mask_path, transparent_output_path, whitebg_output_path))

    if not tasks:
        logger.warning("No valid image pairs found to process")
        return

    logger.info(f"Found {len(tasks)} valid image pairs to process")
    logger.info(f"Skipped: {skipped} (no mask found)")
    logger.info(f"Invalid masks: {invalid_masks}")
    logger.info(f"Invalid pairs: {invalid_pairs}")

    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_single_image, tasks))
    
    elapsed = time.time() - start_time
    processed = sum(1 for r in results if r)
    errors = sum(1 for r in results if not r)
    avg_time = elapsed / len(tasks) if tasks else 0
    
    logger.info(f"Processing complete:")
    logger.info(f"- Successfully processed: {processed}")
    logger.info(f"- Errors: {errors}")
    logger.info(f"- Total time: {elapsed:.1f}s")
    logger.info(f"- Average time per image: {avg_time:.1f}s")
