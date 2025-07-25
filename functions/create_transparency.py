import os
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import logging
from typing import Tuple, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def find_mask_path(specimen_path: str, mask_dir: str) -> Optional[str]:
    """
    Find the corresponding mask for a specimen image with _masked in the filename.
    Supports both tray-based and specimen-only directory structures.
    
    Args:
        specimen_path: Path to the specimen image
        mask_dir: Directory containing mask files
        
    Returns:
        Optional[str]: Path to the mask file or None if not found
    """
    path_parts = os.path.normpath(specimen_path).split(os.sep)
    specimen_name = os.path.splitext(path_parts[-1])[0]
    
    # Remove _masked suffix from specimen name to find the corresponding mask
    specimen_base = specimen_name.replace('_masked', '')
    
    # Method 1: Try tray-based structure (for standard drawers)
    if len(path_parts) >= 4:
        drawer_id = path_parts[-3]
        tray_id = path_parts[-2]
        
        # Check if this follows standard naming pattern
        if '_tray_' in specimen_base and '_spec' in specimen_base:
            mask_subdir = os.path.join(mask_dir, tray_id)
            mask_options = [f"{specimen_base}_fullmask.png", f"{specimen_base}_fullmask_unedited.png"]
            
            for mask_name in mask_options:
                mask_path = os.path.join(mask_subdir, mask_name)
                if os.path.exists(mask_path):
                    return mask_path
    
    # Method 2: Try direct lookup in mask_dir (for specimen-only drawers)
    mask_options = [f"{specimen_base}_fullmask.png", f"{specimen_base}_fullmask_unedited.png"]
    
    # Check for numbered masks as well
    for i in range(1, 10):
        mask_options.append(f"{specimen_base}_fullmask_{i}.png")
    
    # First try the root mask directory
    for mask_name in mask_options:
        direct_mask_path = os.path.join(mask_dir, mask_name)
        if os.path.exists(direct_mask_path):
            return direct_mask_path
    
    # Method 3: Search recursively in subdirectories
    for root, _, files in os.walk(mask_dir):
        for mask_name in mask_options:
            if mask_name in files:
                return os.path.join(root, mask_name)
    
    # Method 4: Try flat structure assuming specimens are not in tray subfolders
    if len(path_parts) >= 2:
        specimens_subdir = path_parts[-2]  # Could be a subfolder within specimens
        for mask_name in mask_options:
            mask_path = os.path.join(mask_dir, specimens_subdir, mask_name)
            if os.path.exists(mask_path):
                return mask_path
            
    return None

def process_single_image(args: Tuple[str, str, str, str]) -> bool:
    """
    Process a single specimen image with its mask to create transparent versions.
    
    Args:
        args: Tuple of (specimen_path, mask_path, transparent_output_path, whitebg_output_path)
        
    Returns:
        bool: True if processed successfully, False otherwise
    """
    specimen_path, mask_path, transparent_output_path, whitebg_output_path = args
    
    if os.path.exists(transparent_output_path):
        return False
        
    try:
        # Load and process images with explicit context management
        with Image.open(specimen_path) as specimen_img:
            specimen_image = specimen_img.convert("RGBA").copy()  # Create copy to detach from file
            
        with Image.open(mask_path) as mask_img:
            mask_image = mask_img.convert("L").copy()  # Create copy to detach from file
                
        # Enhance the mask for clearer edges
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
        
        # Explicitly close all images to prevent cleanup issues
        enhanced_mask.close()
        alpha.close()
        transparent_image.close()
        white_bg.close()
        specimen_image.close()
        mask_image.close()
        
        return True
                
    except Exception as e:
        print(f"Error: {os.path.basename(specimen_path)} - {str(e)}")
        return False

def determine_optimal_workers(total_files: int, sequential: bool = False, max_workers: Optional[int] = None) -> int:
    """
    Determine optimal number of worker processes based on configuration and available resources.
    
    Args:
        total_files: Number of files to process
        sequential: If True, use only 1 worker
        max_workers: Maximum number of workers to use
        
    Returns:
        int: Number of workers to use
    """
    if sequential:
        return 1
        
    cpu_cores = multiprocessing.cpu_count()
    
    # Default to 75% of cores for large batches
    if total_files > 10:
        workers = min(max(1, cpu_cores * 3 // 4), total_files)
    else:
        # For small batches, use 50% of cores
        workers = min(max(1, cpu_cores // 2), total_files)
    
    # Apply max_workers constraint if specified
    if max_workers is not None:
        workers = min(workers, max_workers)
        
    return workers

def create_transparency(specimen_input_dir: str, mask_input_dir: str, 
                      transparent_output_dir: str, whitebg_output_dir: str,
                      sequential: bool = False, max_workers: Optional[int] = None, 
                      batch_size: Optional[int] = None) -> None:
    """
    Create transparent and white background versions of specimens using masks.
    Supports both tray-based and specimen-only directory structures.
    
    Args:
        specimen_input_dir: Directory containing specimen images (with _masked in filenames)
        mask_input_dir: Directory containing mask files
        transparent_output_dir: Directory to save transparent images
        whitebg_output_dir: Directory to save white background images
        sequential: If True, process one at a time
        max_workers: Maximum number of parallel workers
        batch_size: Process images in batches of this size
    """
    tasks: List[Tuple[str, str, str, str]] = []
    missing_masks = 0

    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    for root, _, files in os.walk(specimen_input_dir):
        for file in (f for f in files if f.lower().endswith(supported_formats) and '_masked' in f):
            specimen_path = os.path.join(root, file)
            mask_path = find_mask_path(specimen_path, mask_input_dir)
            
            if not mask_path:
                missing_masks += 1
                continue
                
            # Create output structure that mirrors input structure
            relative_path = os.path.relpath(root, specimen_input_dir)
            if relative_path == '.':
                # Files are in the root - put outputs in root of output dirs
                transparent_subfolder = transparent_output_dir
                whitebg_subfolder = whitebg_output_dir
            else:
                # Files are in subdirectories - mirror the structure
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

    if missing_masks > 0:
        print(f"Warning: {missing_masks} specimens had no corresponding masks")

    # Determine optimal worker count based on configuration
    num_workers = determine_optimal_workers(len(tasks), sequential, max_workers)
    print(f"Processing {len(tasks)} images with {num_workers} workers")
    
    # Initialize tracking variables
    processed = 0
    skipped = 0
    
    # Process in batches if batch_size is specified
    if batch_size and batch_size < len(tasks):
        print(f"Processing in batches of {batch_size}")
        total_batches = (len(tasks) + batch_size - 1) // batch_size
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i+batch_size]
            batch_num = i//batch_size + 1
            
            # Show batch progress
            print(f"\rProcessing batch {batch_num}/{total_batches} [{i}/{len(tasks)} images]", end="", flush=True)
            
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                batch_results = list(executor.map(process_single_image, batch))
                
            batch_processed = sum(1 for r in batch_results if r)
            batch_skipped = sum(1 for r in batch_results if not r)
            processed += batch_processed
            skipped += batch_skipped
            
            # Update progress after each batch
            print(f"\rProcessed {i + len(batch)}/{len(tasks)} images", end="", flush=True)
            
        print()  # Final newline after batches complete
    else:
        # Process all at once with progress indicator
        progress_interval = 100  # Update progress bar every 100 images
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(process_single_image, task) for task in tasks]
            
            for i, future in enumerate(futures):
                result = future.result()
                if result:
                    processed += 1
                else:
                    skipped += 1