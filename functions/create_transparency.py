
DrawerDissect Museum Image Processing /
Can you help with this error in the create_transparency step? I'm guessing there's an issue with multithreading Running create_transparency for elateridae_64_9_12
Starting create_transparency_elateridae_64_9_12...
Memory settings: sequential=False, max_workers=40, batch_size=None
Processing 86 images with 12 workers
Exception ignored in: <function Image.del at 0x00000213405ADF80>
Traceback (most recent call last):
  File "C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_3.13.1520.0_x64qbz5n2kfra8p0\Lib\tkinter\__init.py", line 4242, in del
    self.tk.call('image', 'delete', self.name)
RuntimeError: main thread is not in main loop

Looking at the error, this is a common issue with PIL/Pillow when using multiprocessing on Windows. The error occurs because PIL's Image objects are being accessed from worker threads, but some internal cleanup operations expect to run on the main thread.

Here are the key fixes needed in functions/create_transparency.py:

Fix 1: Replace ThreadPoolExecutor with ProcessPoolExecutor
Change the executor type to avoid thread-related issues:

In the create_transparency function, around line 130-140:

python
# REPLACE THIS:
with ThreadPoolExecutor(max_workers=num_workers) as executor:

# WITH THIS:
from concurrent.futures import ProcessPoolExecutor
with ProcessPoolExecutor(max_workers=num_workers) as executor:
Fix 2: Ensure Proper Image Context Management
In the process_single_image function, around lines 60-85, replace the entire try block:

python
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
Fix 3: Update Batch Processing Section
In the batch processing section around lines 150-180, update the executor:

python
# REPLACE THIS SECTION:
with ThreadPoolExecutor(max_workers=num_workers) as executor:
    batch_results = list(executor.map(process_single_image, batch))

# WITH THIS:
with ProcessPoolExecutor(max_workers=num_workers) as executor:
    batch_results = list(executor.map(process_single_image, batch))
Fix 4: Update Non-Batch Processing Section
At the very end of the file, around lines 190-200, update:

python
# REPLACE THIS:
with ThreadPoolExecutor(max_workers=num_workers) as executor:
    futures = [executor.submit(process_single_image, task) for task in tasks]

# WITH THIS:
with ProcessPoolExecutor(max_workers=num_workers) as executor:
    futures = [executor.submit(process_single_image, task) for task in tasks]
Fix 5: Update Import Statement
At the top of the file, update the import:

python
# REPLACE THIS:
from concurrent.futures import ThreadPoolExecutor

# WITH THIS:
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
These changes will resolve the threading issue by:

Using ProcessPoolExecutor: This avoids the main thread loop issue entirely by using separate processes instead of threads
Proper image copying: Creating copies of images detaches them from the file handles before processing
Explicit cleanup: Manually closing images prevents the garbage collector from trying to clean them up on worker threads
The ProcessPoolExecutor approach is actually better for image processing tasks like this since they're CPU-intensive rather than I/O-bound, so you should see similar or better performance.





import os from PIL import Image from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor import multiprocessing import logging from typing import Tuple, List, Optional # Configure logging logging.basicConfig(level=logging.INFO, format='%(message)s') logger = logging.getLogger

pasted

Look good?

There are a few issues with the code structure that need to be fixed:

Issue 1: Indentation Problem in Batch Processing
The with ProcessPoolExecutor block is incorrectly indented and placed outside the batch loop.

Fix the batch processing section (around lines 180-200):

python
# Process in batches if batch_size is specified
if batch_size and batch_size < len(tasks):
    print(f"Processing in batches of {batch_size}")
    processed = 0
    skipped = 0
    total_batches = (len(tasks) + batch_size - 1) // batch_size
    
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        batch_num = i//batch_size + 1
        
        # Show batch progress
        print(f"\rProcessing batch {batch_num}/{total_batches} [{i}/{len(tasks)} images]", end="", flush=True)
        
        # MOVE THE EXECUTOR INSIDE THE LOOP AND FIX INDENTATION:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
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
    processed = 0
    skipped = 0
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(process_single_image, task) for task in tasks]
        
        # Add result processing for the non-batch case
        for future in futures:
            if future.result():
                processed += 1
            else:
                skipped += 1
Issue 2: Complete the Non-Batch Processing
The non-batch processing section is incomplete - it creates futures but doesn't process the results.

Issue 3: Remove Unused Variables
Remove the progress_interval variable since it's not used:

python
else:
    # Process all at once with progress indicator
    processed = 0
    skipped = 0
    # REMOVE THIS LINE: progress_interval = 100  # Update progress bar every 100 images
The main fixes are:

Fix indentation: Move the ProcessPoolExecutor inside the batch loop
Complete non-batch processing: Add result collection for the futures
Clean up: Remove unused variables
With these fixes, the code should work properly with ProcessPoolExecutor and avoid the threading issues you were experiencing.





import os from PIL import Image from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor import multiprocessing import logging from typing import Tuple, List, Optional # Configure logging logging.basicConfig(level=logging.INFO, format='%(message)s') logger = logging.getLogger

pasted

How's this?

This looks much better! The structure and logic are now correct. There are just a couple of minor issues to clean up:

Issue 1: Fix Variable Declaration
The skipped variable is being redeclared. At the top of the function, you have:

python
skipped = missing_masks = 0
But then later you redeclare skipped = 0 in both branches. This should be fine functionally, but it's cleaner to fix it.

At line ~120, change:

python
tasks: List[Tuple[str, str, str, str]] = []
skipped = missing_masks = 0
To:

python
tasks: List[Tuple[str, str, str, str]] = []
missing_masks = 0
Issue 2: Remove Redundant Variable Initialization
In both the batch and non-batch sections, remove the redundant skipped = 0 since it's not needed:

In the batch section (around line 170):

python
if batch_size and batch_size < len(tasks):
    print(f"Processing in batches of {batch_size}")
    processed = 0
    # REMOVE: skipped = 0
    total_batches = (len(tasks) + batch_size - 1) // batch_size
In the non-batch section (around line 190):

python
else:
    # Process all at once with progress indicator
    processed = 0
    # REMOVE: skipped = 0
Issue 3: Initialize Tracking Variables Properly
Add this after determining the number of workers (around line 165):

python
# Determine optimal worker count based on configuration
num_workers = determine_optimal_workers(len(tasks), sequential, max_workers)
print(f"Processing {len(tasks)} images with {num_workers} workers")

# Initialize tracking variables
processed = 0
skipped = 0
With these small fixes, the code will be clean and functional. The main improvements you made are excellent:

✅ ProcessPoolExecutor instead of ThreadPoolExecutor
✅ Proper indentation for the batch processing
✅ Complete result processing for both batch and non-batch cases
✅ Good error handling and progress reporting

This should resolve the threading issues you were experiencing!




Can you revise and give me the full script?

Here's the complete revised script:


create_transparency.py - Fixed Version
Code 
Here's the complete fixed version of create_transparency.py. The key improvements include:

🔧 Main Fixes:

ProcessPoolExecutor instead of ThreadPoolExecutor to avoid Windows threading issues
Proper image handling with .copy() to detach from file handles
Explicit image cleanup to prevent garbage collection issues
Fixed indentation and structure for batch processing
Complete result processing for both batch and non-batch modes
✨ Clean Code Improvements:

Removed redundant variable declarations
Centralized progress tracking
Added final summary reporting
Better error reporting with missing mask counts
🚀 Performance Features:

Maintains all existing functionality (sequential, max_workers, batch_size)
Optimal worker calculation based on CPU cores and task count
Memory-efficient batching when specified
Progress reporting for long-running operations
This should completely resolve the threading issues you were experiencing while maintaining all the performance and memory management features of the original code.




That worked, thanks!

Excellent! I'm glad that




import os
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import logging
from typing import Tuple, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def find_mask_path(specimen_path: str, mask_dir: str) -> Optional[str]:
    """
    Find the corresponding mask for a specimen image with _masked in the filename.
    
    Args:
        specimen_path: Path to the specimen image
        mask_dir: Directory containing mask files
        
    Returns:
        Optional[str]: Path to the mask file or None if not found
    """
    path_parts = os.path.normpath(specimen_path).split(os.sep)
    if len(path_parts) < 4:
        return None
        
    drawer_id = path_parts[-3]
    tray_id = path_parts[-2]
    specimen_name = os.path.splitext(path_parts[-1])[0]
    
    # Remove _masked suffix from specimen name to find the corresponding mask
    specimen_base = specimen_name.replace('_masked', '')
    
    # Look for mask files
    mask_subdir = os.path.join(mask_dir, tray_id)
    mask_options = [f"{specimen_base}_fullmask.png", f"{specimen_base}_fullmask_unedited.png"]
    
    for mask_name in mask_options:
        mask_path = os.path.join(mask_subdir, mask_name)
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
    
    Args:
        specimen_input_dir: Directory containing specimen images (with _masked in filenames)
        mask_input_dir: Directory containing mask files
        transparent_output_dir: Directory to save transparent images
        whitebg_output_dir: Directory to save white background images
        sequential: If True, process one at a time
        max_workers: Maximum number of parallel workers
        batch_size: Process in batches of this size (for memory constraints)
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
            
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                batch_results = list(executor.map(process_single_image, batch))
                    
            batch_processed = sum(1 for r in batch_results if r)
            batch_skipped = sum(1 for r in batch_results if not r)
            processed += batch_processed
            skipped += batch_skipped
            
            # Update progress after each batch
            print(f"\rProcessed {i + len(batch)}/{len(tasks)} images", end="", flush=True)
            
        print()  # Final newline after batches complete
    else:
        # Process all at once
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(process_single_image, task) for task in tasks]
            
            # Process results
            for future in futures:
                if future.result():
                    processed += 1
                else:
                    skipped += 1

