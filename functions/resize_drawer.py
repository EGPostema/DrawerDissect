from PIL import Image, ImageFile
import os
import time
from pathlib import Path
from multiprocessing import Pool, cpu_count
from typing import List, Set, Tuple, Optional

# Import simplified logging
from logging_utils import (
    log, 
    log_found,
    log_found_previous,
    log_progress, 
    log_skipped,
    increment_processed, 
    increment_skipped
)

# Allow PIL to handle very large images
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def determine_optimal_workers(total_files: int, sequential: bool = False, max_workers: Optional[int] = None) -> int:
    """
    Determine optimal number of worker processes.
    """
    # If sequential processing is requested, use 1 worker
    if sequential:
        return 1
        
    # If max_workers is specified, respect that limit
    if max_workers is not None:
        return min(max_workers, total_files)
    
    # Default: Use half the available cores
    cpu_cores = cpu_count()
    return min(max(1, cpu_cores // 2), total_files)

def resize_image(args: Tuple[str, str, Set[str], int, int]) -> bool:
    """
    Resize a single image file.
    Returns True if processed, False if skipped.
    """
    input_path, output_dir, completed_files, current, total = args
    filename = Path(input_path).name
    base_name = Path(input_path).stem
    output_filename = f"{base_name}_1000.jpg"
    
    if output_filename in completed_files:
        log_progress("resize_drawers", current, total, f"Skipped (already exists)")
        increment_skipped("resize_drawers")
        return False
        
    try:
        output_path = Path(output_dir) / output_filename
        
        # Open and resize image
        with Image.open(input_path) as img:
            # Use draft mode for faster loading
            if hasattr(img, 'draft'):
                img.draft('RGB', (1000, 1000))
            
            # Convert if needed
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Resize and save
            scale_factor = min(1000 / dim for dim in img.size)
            new_size = tuple(int(dim * scale_factor) for dim in img.size)
            resized = img.resize(new_size, Image.Resampling.BILINEAR)
            resized.save(output_path, 'JPEG', quality=95, optimize=True, progressive=True)
        
        log_progress("resize_drawers", current, total, filename)
        increment_processed("resize_drawers")
        return True
            
    except Exception as e:
        log(f"Error processing {filename}: {str(e)}")
        return False

def get_image_files(input_dir: str) -> List[str]:
    """Get all supported image files from input directory."""
    supported_formats = {'.jpg', '.jpeg', '.tif', '.tiff', '.png'}
    return [
        str(p) for p in Path(input_dir).rglob('*')
        if p.suffix.lower() in supported_formats
    ]

def resize_drawer_images(
    input_dir: str, 
    output_dir: str, 
    sequential: bool = False,
    max_workers: Optional[int] = None,
    batch_size: Optional[int] = None
) -> None:
    """
    Resize all images in input_dir to 1000px max dimension and save to output_dir.
    
    Args:
        input_dir: Directory containing input images
        output_dir: Directory to save resized images
        sequential: Process images one at a time (for memory constraints)
        max_workers: Maximum number of parallel workers
        batch_size: Process in batches of this size (for memory constraints)
    """
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get existing files and input files
    completed_files = {f.name for f in Path(output_dir).glob('*_1000.jpg')}
    file_paths = get_image_files(input_dir)
    total_files = len(file_paths)
    
    if not file_paths:
        log("No images found to process")
        return
    
    log_found("images", total_files)
    if completed_files:
        log_found_previous("images", len(completed_files))
    
    # Determine parallelization settings
    if sequential:
        log("Processing images sequentially to conserve memory...")
        
    num_workers = determine_optimal_workers(total_files, sequential, max_workers)
    
    # Process images
    args = [(f, output_dir, completed_files, i+1, total_files) 
            for i, f in enumerate(file_paths)]
    
    # Process in parallel or sequentially based on settings
    if num_workers > 1 and not sequential:
        with Pool(num_workers) as pool:
            results = pool.map(resize_image, args)
    else:
        # Process sequentially
        results = []
        for arg in args:
            results.append(resize_image(arg))