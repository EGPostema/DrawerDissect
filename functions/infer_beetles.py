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
    """Creates a temporary JPG version if the image is a TIFF."""
    if image_path.lower().endswith((".jpg", ".jpeg", ".png")):
        yield image_path
    else:
        temp_dir = os.path.dirname(image_path)
        with tempfile.NamedTemporaryFile(suffix=".jpg", dir=temp_dir, delete=False) as tmp:
            temp_file_path = tmp.name
        try:
            with Image.open(image_path) as img:
                if img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
                ):
                    img = img.convert("RGB")
                img.save(temp_file_path, "JPEG", quality=90)
            yield temp_file_path
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)


def retry_with_backoff(func, max_retries=3, base_delay=2, max_delay=60):
    """Retry a function with exponential backoff on server errors."""
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            error_str = str(e).lower()
            is_server_error = any(
                kw in error_str
                for kw in ("500", "internal server error", "server error", "timeout", "connection")
            )
            if is_server_error and attempt < max_retries:
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                log(f"Server error (attempt {attempt + 1}/{max_retries + 1}), retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                raise
    raise Exception(f"Failed after {max_retries + 1} attempts")


def process_image(args):
    """Process a single specimen image."""
    model_runner, input_dir, output_dir, root, file, confidence, current, total = args

    relative_path = os.path.relpath(root, input_dir)
    output_subfolder = output_dir if relative_path == "." else os.path.join(output_dir, relative_path)
    os.makedirs(output_subfolder, exist_ok=True)

    json_path = os.path.join(output_subfolder, os.path.splitext(file)[0] + ".json")

    if os.path.exists(json_path):
        log_progress("outline_specimens", current, total, "Skipped")
        return False

    file_path = os.path.join(root, file)

    try:
        def run_inference():
            with temporary_jpg_if_needed(file_path) as inference_path:
                return model_runner.predict(inference_path, confidence=confidence)

        prediction = retry_with_backoff(run_inference, max_retries=3, base_delay=2)

        with open(json_path, "w") as f:
            json.dump(prediction, f)

        log_progress("outline_specimens", current, total, "Processed")
        return True

    except Exception as e:
        log(f"Error processing {file}: {str(e)}")
        return False


def infer_beetles(
    input_dir: str,
    output_dir: str,
    model_runner,
    confidence: Optional[float] = 50,
    max_workers: Optional[int] = None,
    sequential: bool = False,
):
    """
    Segment specimens in images.

    Args:
        input_dir:    Directory containing specimen images
        output_dir:   Directory to save JSON outputs
        model_runner: A RoboflowModelRunner or LocalModelRunner instance
        confidence:   Confidence threshold (0-100)
        max_workers:  Max parallel workers (None = auto)
        sequential:   Process one at a time (lower memory usage)
    """
    image_files = []
    supported_formats = (".jpg", ".jpeg", ".tif", ".tiff", ".png")

    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(supported_formats):
                image_files.append((root, file))

    if not image_files:
        log("No specimen images found to process")
        return

    log_found("specimen images", len(image_files))

    tasks = [
        (model_runner, input_dir, output_dir, root, file, confidence, i + 1, len(image_files))
        for i, (root, file) in enumerate(image_files)
    ]

    processed = 0
    skipped = 0
    errors = 0

    if sequential:
        log("Processing images sequentially")
        for task in tasks:
            try:
                result = process_image(task)
                processed += bool(result)
                skipped += not bool(result)
            except Exception as e:
                log(f"Error in task: {e}")
                errors += 1
    else:
        workers = max_workers if max_workers is not None else min(32, os.cpu_count() * 2)
        log(f"Processing images in parallel with {workers} workers")
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(process_image, tasks))
            processed = sum(1 for r in results if r)
            skipped = len(tasks) - processed - errors

    log(f"outline_specimens complete: {processed} processed, {skipped} skipped, {errors} errors")
