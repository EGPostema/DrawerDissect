from PIL import Image, ImageFile
import os
import time
from pathlib import Path
from multiprocessing import Pool, cpu_count
from typing import List, Set, Tuple

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def determine_optimal_workers(total_files: int) -> int:
    """
    Determine optimal number of worker processes based on:
    - Number of files to process
    - Available CPU cores
    """
    cpu_cores = cpu_count()
    
    # For single file, don't parallelize
    if total_files == 1:
        return 1
        
    # For large batches (>10 files), use up to 75% of cores
    if total_files > 10:
        return min(max(1, cpu_cores * 3 // 4), total_files)
    
    # For small batches (2-10 files), use up to 50% of cores
    return min(max(1, cpu_cores // 2), total_files)

def resize_image(args: Tuple[str, str, Set[str], int, int]) -> bool:
    """
    Optimized resize for large images
    Returns True if processed, False if skipped
    """
    input_path, output_dir, completed_files, current, total = args
    filename = Path(input_path).name
    base_name = Path(input_path).stem
    output_filename = f"{base_name}_1000.jpg"
    
    if output_filename in completed_files:
        print(f"\rProcessing image {current}/{total} - Skipped {filename} (already exists)", 
              end="", flush=True)
        return False
        
    try:
        output_path = Path(output_dir) / output_filename
        start_time = time.time()
        
        # Open and resize image with optimizations
        with Image.open(input_path) as img:
            # Use draft mode for faster loading
            if hasattr(img, 'draft'):
                img.draft('RGB', (1000, 1000))
            
            # Convert only if necessary
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Calculate dimensions once
            scale_factor = min(1000 / dim for dim in img.size)
            new_size = tuple(int(dim * scale_factor) for dim in img.size)
            
            # Resize with BILINEAR (faster than LANCZOS, good enough for downscaling)
            resized = img.resize(new_size, Image.Resampling.BILINEAR)
            
            # Optimize save operation
            resized.save(
                output_path,
                'JPEG',
                quality=95,
                optimize=True,
                progressive=True
            )
        
        duration = time.time() - start_time
        print(f"\rProcessing image {current}/{total} - Completed {filename} in {duration:.1f}s", 
              end="", flush=True)
        return True
            
    except Exception as e:
        print(f"\rProcessing image {current}/{total} - Error with {filename}: {str(e)}", 
              end="", flush=True)
        return False

def get_image_files(input_dir: str) -> List[str]:
    """Get all supported image files from input directory"""
    supported_formats = {'.jpg', '.jpeg', '.tif', '.tiff', '.png'}
    return [
        str(p) for p in Path(input_dir).rglob('*')
        if p.suffix.lower() in supported_formats
    ]

def resize_tray_images(input_dir: str, output_dir: str) -> None:
    start_time = time.time()
    
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get existing files and input files
    completed_files = {f.name for f in Path(output_dir).glob('*_1000.jpg')}
    file_paths = get_image_files(input_dir)
    total_files = len(file_paths)
    
    if not file_paths:
        print("No images found to process")
        return
    
    print(f"Found {total_files} images to process")
    if completed_files:
        print(f"Found {len(completed_files)} previously processed images")
    
    # Determine optimal number of workers
    num_workers = determine_optimal_workers(total_files)
    
    # Process images
    args = [(f, output_dir, completed_files, i+1, total_files) 
            for i, f in enumerate(file_paths)]
    
    with Pool(num_workers) as pool:
        results = pool.map(resize_image, args)
        processed = sum(1 for r in results if r)
    
    # Final summary
    total_time = time.time() - start_time
    print(f"\nProcessing complete:")
    print(f"- {processed} images processed")
    print(f"- {total_files - processed} images skipped")
    print(f"- Total time: {total_time:.1f}s")





