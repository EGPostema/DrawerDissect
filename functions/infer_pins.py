import os
import json
import time
import random
import tempfile
from PIL import Image
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
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
                img.save(temp_file_path, 'JPEG', quality=95)
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
    """Process a single image to detect pins."""
    model, input_dir, output_dir, root, file, confidence, current, total = args
    
    # Create output subfolder with the same structure
    relative_path = os.path.relpath(root, input_dir)
    output_subfolder = os.path.join(output_dir, relative_path)
    os.makedirs(output_subfolder, exist_ok=True)
    
    # Define the JSON filename and path
    json_filename = file.rsplit('.', 1)[0] + '.json'
    json_path = os.path.join(output_subfolder, json_filename)
    
    # Skip if already processed
    if os.path.exists(json_path):
        log_progress("outline_pins", current, total, f"Skipped (already exists)")
        return False
        
    file_path = os.path.join(root, file)
    
    try:
        def run_inference():
            # Handle temporary conversion for TIFFs if needed
            with temporary_jpg_if_needed(file_path) as inference_path:
                # Run inference
                return model.predict(inference_path, confidence=confidence).json()
        
        # Use retry logic for the inference call
        prediction = retry_with_backoff(run_inference, max_retries=3, base_delay=2)
        
        # Save predictions to a JSON file
        with open(json_path, 'w') as json_file:
            json.dump(prediction, json_file)
            
        # Count pins found
        pin_count = len(prediction.get('predictions', []))
        log_progress("outline_pins", current, total, f"Found {pin_count} pins")
        return True
        
    except Exception as e:
        log(f"Error processing {file}: {e}")
        return False

def infer_pins(
    input_dir, 
    output_dir, 
    csv_path, 
    rf_instance, 
    workspace_instance, 
    model_endpoint, 
    version, 
    confidence=50,
    sequential=False,
    max_workers=None
):
    """
    Detect pins in specimen images using the Roboflow model.
    
    Args:
        input_dir: Directory containing masked specimen images
        output_dir: Directory to save prediction coordinates
        csv_path: Path to measurements CSV (not used in this simplified version)
        rf_instance: Roboflow instance
        workspace_instance: Workspace instance from Roboflow
        model_endpoint: Name of the model
        version: Version number of the model
        confidence: Confidence threshold (0-100)
        sequential: Whether to process sequentially to save memory
        max_workers: Maximum number of concurrent workers (None = auto)
    """
    # Initialize model
    log(f"Using model: {model_endpoint} v{version} (confidence: {confidence})")
    project = workspace_instance.project(model_endpoint)
    model = project.version(version).model
    
    # Find all masked specimen images
    image_files = []
    valid_extensions = ('.tif', '.tiff', '.png', '.jpg', '.jpeg')
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            # Check for valid extensions and '_masked' in the filename
            if not file.lower().endswith(valid_extensions) or '_masked' not in file:
                continue
            
            image_files.append((root, file))
    
    if not image_files:
        log("No masked specimen images found to process")
        return
        
    log_found("masked specimens", len(image_files))
    
    # Prepare tasks with progress tracking indices
    tasks = [(model, input_dir, output_dir, root, file, confidence, i+1, len(image_files)) 
             for i, (root, file) in enumerate(image_files)]
    
    # Counters for tracking results
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
        
        # Use ThreadPoolExecutor for I/O bound tasks
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(process_image, tasks))
            processed = sum(1 for r in results if r)
            skipped = len(tasks) - processed - errors
    
    log(f"Complete. {processed} processed, {skipped} skipped, {errors} errors")


