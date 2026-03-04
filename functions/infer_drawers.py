import os
import json
from logging_utils import log, log_found, log_progress


def infer_drawers(input_dir, output_dir, model_runner, confidence=50, overlap=50):
    """
    Detect trays in drawer images.

    Args:
        input_dir:    Directory containing resized drawer images
        output_dir:   Directory to save prediction JSON files
        model_runner: A RoboflowModelRunner or LocalModelRunner instance
                      (from functions/model_runner.py)
        confidence:   Detection confidence threshold (0-100)
        overlap:      Bounding-box overlap threshold (0-100)
    """
    os.makedirs(output_dir, exist_ok=True)

    # Find all resized drawer images
    image_files = []
    for root, _, files in os.walk(input_dir):
        for f in files:
            if f.endswith("_1000.jpg"):
                image_files.append(os.path.join(root, f))

    total_files = len(image_files)
    log_found("images", total_files)

    processed = 0
    skipped = 0

    for i, file_path in enumerate(image_files, 1):
        filename = os.path.basename(file_path)
        json_path = os.path.join(output_dir, filename.replace(".jpg", ".json"))

        if os.path.exists(json_path):
            log_progress("find_trays", i, total_files, "Skipped (already exists)")
            skipped += 1
            continue

        try:
            prediction = model_runner.predict(file_path, confidence=confidence, overlap=overlap)

            with open(json_path, "w") as json_file:
                json.dump(prediction, json_file)

            tray_count = len(prediction.get("predictions", []))
            log_progress("find_trays", i, total_files, f"Found {tray_count} trays")
            processed += 1

        except Exception as e:
            log(f"Error processing {filename}: {str(e)}")

    log(f"find_trays complete: {processed} processed, {skipped} skipped")
