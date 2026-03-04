import os
import json
from logging_utils import log, log_found, log_progress


def infer_tray_images(input_dir, output_dir, model_runner, confidence=50, overlap=50):
    """
    Detect specimens in tray images.

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
                image_files.append((os.path.join(root, file), file))

    total_files = len(image_files)

    if not total_files:
        log("No resized tray images found to process")
        return

    log_found("images", total_files)

    existing_files = [
        f.replace("_1000.json", "_1000.jpg")
        for f in os.listdir(output_dir)
        if f.endswith("_1000.json")
    ]
    if existing_files:
        log(f"Found {len(existing_files)} previously processed images")

    processed = 0
    skipped = 0
    errors = 0

    for i, (file_path, file_name) in enumerate(image_files, 1):
        # Mirror directory structure in output
        relative_path = os.path.relpath(os.path.dirname(file_path), input_dir)
        if relative_path != ".":
            output_subdir = os.path.join(output_dir, relative_path)
            os.makedirs(output_subdir, exist_ok=True)
        else:
            output_subdir = output_dir

        json_path = os.path.join(output_subdir, file_name.replace(".jpg", ".json"))

        if os.path.exists(json_path):
            log_progress("find_specimens", i, total_files, "Skipped (already exists)")
            skipped += 1
            continue

        try:
            prediction = model_runner.predict(file_path, confidence=confidence, overlap=overlap)

            with open(json_path, "w") as json_file:
                json.dump(prediction, json_file)

            count = len(prediction.get("predictions", []))
            log_progress("find_specimens", i, total_files, f"Found {count} specimens")
            processed += 1

        except Exception as e:
            log(f"Error processing {file_name}: {str(e)}")
            errors += 1

    log(f"find_specimens complete: {processed} processed, {skipped} skipped, {errors} errors")
