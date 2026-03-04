import os
import json
import tempfile
from PIL import Image
from contextlib import contextmanager
from logging_utils import log, log_found, log_progress


@contextmanager
def temporary_jpg_if_needed(image_path):
    """Creates a temporary JPG version if the image is a TIFF."""
    if image_path.lower().endswith((".jpg", ".jpeg", ".png")):
        yield image_path
    else:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as tmp:
            with Image.open(image_path) as img:
                if img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
                ):
                    img = img.convert("RGB")
                img.save(tmp.name, "JPEG", quality=95)
            yield tmp.name


def infer_tray_labels(input_dir, output_dir, model_runner, confidence=50, overlap=50):
    """
    Detect label components in tray images.

    Args:
        input_dir:    Directory containing resized tray images
        output_dir:   Directory to save prediction JSON files
        model_runner: A RoboflowModelRunner or LocalModelRunner instance
        confidence:   Detection confidence threshold (0-100)
        overlap:      Bounding-box overlap threshold (0-100)
    """
    os.makedirs(output_dir, exist_ok=True)

    # Find all resized tray images recursively
    image_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith("_1000.jpg"):
                image_files.append((os.path.join(root, file), file, root))

    total_files = len(image_files)

    if not total_files:
        log("No resized tray images found to process")
        return

    log_found("images", total_files)

    # Track already-processed files
    existing_files = []
    for root, _, files in os.walk(output_dir):
        for file in files:
            if file.endswith("_1000_label.json"):
                existing_files.append(file.replace("_1000_label.json", "_1000.jpg"))
    if existing_files:
        log(f"Found {len(existing_files)} previously processed images")

    processed = 0
    skipped = 0
    errors = 0

    for i, (file_path, file_name, file_root) in enumerate(image_files, 1):
        # Mirror directory structure in output
        relative_path = os.path.relpath(file_root, input_dir)
        if relative_path != ".":
            output_subdir = os.path.join(output_dir, relative_path)
            os.makedirs(output_subdir, exist_ok=True)
        else:
            output_subdir = output_dir

        json_name = file_name.replace("_1000.jpg", "_1000_label.json")
        json_path = os.path.join(output_subdir, json_name)

        if os.path.exists(json_path):
            log_progress("find_traylabels", i, total_files, "Skipped (already exists)")
            skipped += 1
            continue

        try:
            with temporary_jpg_if_needed(file_path) as inference_path:
                prediction = model_runner.predict(
                    inference_path, confidence=confidence, overlap=overlap
                )

            with open(json_path, "w") as json_file:
                json.dump(prediction, json_file)

            count = len(prediction.get("predictions", []))
            log_progress("find_traylabels", i, total_files, f"Found {count} labels")
            processed += 1

        except Exception as e:
            log(f"Error processing {file_name}: {str(e)}")
            errors += 1

    log(f"find_traylabels complete: {processed} processed, {skipped} skipped, {errors} errors")
