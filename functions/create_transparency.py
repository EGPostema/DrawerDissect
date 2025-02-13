import os
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
import logging
from typing import Tuple, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def validate_mask(mask_path: str) -> bool:
    try:
        with Image.open(mask_path) as mask:
            mask_gray = mask.convert('L')
            values = set(mask_gray.getdata())
            filtered_values = {v for v in values if v > 5 and v < 250}
            if len(filtered_values) > 2:
                print(f"Error: Invalid mask values in {os.path.basename(mask_path)}")
                return False
            return True
    except Exception as e:
        print(f"Error: Failed to validate mask {os.path.basename(mask_path)} - {str(e)}")
        return False

def validate_image_pair(specimen_path: str, mask_path: str) -> bool:
    try:
        with Image.open(specimen_path) as specimen, Image.open(mask_path) as mask:
            spec_ratio = specimen.size[0] / specimen.size[1]
            mask_ratio = mask.size[0] / mask.size[1]
            if abs(spec_ratio - mask_ratio) > 0.01:
                print(f"Error: Aspect ratio mismatch in {os.path.basename(specimen_path)}")
                return False
            return True
    except Exception as e:
        print(f"Error: Failed to validate pair {os.path.basename(specimen_path)} - {str(e)}")
        return False

def process_single_image(args: Tuple[str, str, str, str]) -> bool:
    specimen_path, mask_path, transparent_output_path, whitebg_output_path = args
    
    if os.path.exists(transparent_output_path):
        return False
        
    try:
        with Image.open(specimen_path).convert("RGBA") as specimen_image:
            with Image.open(mask_path).convert("L") as mask_image:
                if specimen_image.size != mask_image.size:
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
                
                print(f"Processed: {os.path.basename(specimen_path)}")
                return True
                
    except Exception as e:
        print(f"Error: {os.path.basename(specimen_path)} - {str(e)}")
        return False

def find_mask_path(specimen_path: str, mask_dir: str) -> Optional[str]:
    path_parts = os.path.normpath(specimen_path).split(os.sep)
    if len(path_parts) < 4:
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
            
    return None

def create_transparency(specimen_input_dir: str, mask_input_dir: str, transparent_output_dir: str, whitebg_output_dir: str) -> None:
    tasks: List[Tuple[str, str, str, str]] = []
    skipped = invalid_masks = invalid_pairs = 0

    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    for root, _, files in os.walk(specimen_input_dir):
        for file in (f for f in files if f.lower().endswith(supported_formats)):
            specimen_path = os.path.join(root, file)
            mask_path = find_mask_path(specimen_path, mask_input_dir)
            
            if not mask_path:
                skipped += 1
                continue
                
            if not validate_mask(mask_path):
                invalid_masks += 1
                continue
                
            if not validate_image_pair(specimen_path, mask_path):
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
        print("No valid image pairs found")
        return

    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_single_image, tasks))
    
    processed = sum(1 for r in results if r)
    errors = sum(1 for r in results if not r)
    
    print(f"\nComplete. Processed: {processed}, Errors: {errors}")
    print(f"Validation: {skipped} missing masks, {invalid_masks} invalid masks, {invalid_pairs} mismatched pairs")
