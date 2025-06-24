import os
import json
import time
import random
import tempfile
from PIL import Image
from contextlib import contextmanager
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from logging_utils import log, log_found, log_progress

@contextmanager
def temporary_jpg_if_needed(image_path):
    """Creates temporary JPG version if image is TIFF."""
    if image_path.lower().endswith(('.jpg', '.jpeg', '.png')):
        yield image_path
    else:  # Handle TIFFs
        temp_dir = os.path.dirname(image_path)  # Use the same directory as the original file
        with tempfile.NamedTemporaryFile(suffix='.jpg', dir=temp_dir, delete=False) as tmp:
            temp_file_path = tmp.name
        try:
            with Image.open(image_path) as img:
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    img = img.convert('RGB')
                img.save(temp_file_path, 'JPEG', quality=90)  # Lower quality for faster processing
            yield temp_file_path
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

def retry_with_backoff(func, max_retries=3, base_delay=2, max_delay=60):
    """
    Retry function with exponential backoff for server errors.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
    """
    for attempt in range(max_retries + 1):  # +1 to include the initial attempt
        try:
            return func()
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a server error we should retry
            is_server_error = (
                '500' in error_str or 
                'internal server error' in error_str or
                'server error' in error_str or
                'timeout' in error_str or
                'connection' in error_str
            )
            
            if is_server_error and attempt < max_retries:
                # Calculate delay with exponential backoff and jitter
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                log(f"Server error (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                # Re-raise the exception if it's not retryable or we've exhausted retries
                raise
    
    # This shouldn't be reached, but just in case
    raise Exception(f"Failed after {max_retries + 1} attempts")

def process_image(args):
    """Process a single image."""
    model, input_dir, output_dir, root, file, confidence, current, total = args
    
    # Extract path information
    relative_path = os.path.relpath(root, input_dir)
    
    # Create output subfolder
    output_subfolder = os.path.join(output_dir, relative_path)
    os.makedirs(output_subfolder, exist_ok=True)
    
    # Define output JSON path
    json_path = os.path.join(output_subfolder, os.path.splitext(file)[0] + '.json')
    
    # Skip if already processed
    if os.path.exists(json_path):
        log_progress("outline_specimens", current, total, f"Skipped")
        return False
        
    try:
        # Run inference with temporary conversion if needed and retry logic
        file_path = os.path.join(root, file)
        
        def run_inference():
            with temporary_jpg_if_needed(file_path) as inference_path:
                return model.predict(inference_path, confidence=confidence).json()
        
        # Use retry logic for the inference call
        prediction = retry_with_backoff(run_inference, max_retries=3, base_delay=2)
        
        # Save results
        with open(json_path, 'w') as f:
            json.dump(prediction, f, indent=None)  # Remove indentation for smaller files
        
        # Log progress (without point counts for efficiency)
        log_progress("outline_specimens", current, total, f"Processed")
        return True
        
    except Exception as e:
        log(f"Error processing {file}: {str(e)}")
        return False

def infer_beetles(
    input_dir: str,
    output_dir: str,
    rf_instance,
    workspace_instance,
    model_endpoint: str,
    version: int,
    confidence: Optional[float] = 50,
    max_workers: Optional[int] = None,
    sequential: bool = False
):
    """
    Segment specimens in images using the Roboflow model.
    
    Args:
        input_dir: Directory containing specimen images
        output_dir: Directory to save JSON outputs
        rf_instance: Roboflow instance
        workspace_instance: Workspace instance from Roboflow
        model_endpoint: Name of the model
        version: Version number of the model
        confidence: Confidence threshold (0-100)
        max_workers: Maximum number of concurrent workers (None = auto)
        sequential: Whether to process sequentially to save memory
    """
    # Initialize model
    log(f"Using model: {model_endpoint} v{version} (confidence: {confidence})")
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    
    # Find all specimen images
    image_files = []
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(supported_formats):
                image_files.append((root, file))
    
    if not image_files:
        log("No specimen images found to process")
        return
        
    log_found("specimen images", len(image_files))
    
    # Prepare tasks with progress tracking indices
    tasks = [(model, input_dir, output_dir, root, file, confidence, i+1, len(image_files)) 
             for i, (root, file) in enumerate(image_files)]
    
    processed = 0
    skipped = 0
    errors = 0
    
    # Process images based on memory settings
    if sequential:
        log("Processing images sequentially")
        for task in tasks:
            try:
                result = process_image(task)
                if result:
                    processed += 1
                else:
                    skipped += 1
            except Exception as e:
                log(f"Error in task: {e}")
                errors += 1
    else:
        # Determine number of workers
        workers = max_workers if max_workers is not None else min(32, os.cpu_count() * 2)
        log(f"Processing images in parallel with {workers} workers")
        
        # Use ThreadPoolExecutor instead of ProcessPoolExecutor for this task
        # as it's mostly I/O bound and has less overhead
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(process_image, tasks))
            processed = sum(1 for r in results if r)
            skipped = len(tasks) - processed - errors
            
    log(f"Complete. {processed} processed, {skipped} skipped, {errors} errors")







