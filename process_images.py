import os
from resize_drawer import resize_drawer_images
from infer_drawers import infer_drawers
from crop_trays import crop_trays_from_fullsize
from resize_trays import resize_tray_images
from label_transcription import transcribe_labels_and_ids
from infer_trays import infer_tray_images
from crop_specimens import crop_specimens_from_trays

# Define directories
fullsize_dir = 'data/drawers/fullsize'
resized_dir = 'data/drawers/resized'
trays_dir = 'data/drawers/trays'
resized_trays_dir = 'data/drawers/resized_trays'
specimens_dir = 'data/drawers/specimens'

# Ensure necessary directories exist
os.makedirs(resized_dir, exist_ok=True)
os.makedirs(trays_dir, exist_ok=True)
os.makedirs(resized_trays_dir, exist_ok=True)
os.makedirs(specimens_dir, exist_ok=True)

def main():
    # Step 1: Resize Images from Fullsize
    resize_drawer_images(fullsize_dir, resized_dir)

    # Step 2: Run Inference on Resized Images
    infer_drawers(resized_dir)

    # Step 3: Crop Trays from Fullsize Images
    crop_trays_from_fullsize(fullsize_dir, resized_dir, trays_dir)

    # Step 4: Resize Trays
    resize_tray_images(trays_dir, resized_trays_dir)

    # Step 5: Transcribe Labels from Resized Trays
    transcribe_labels_and_ids(resized_trays_dir)

    # Step 6: Run Inference on Trays
    infer_tray_images(resized_trays_dir)

    # Step 7: Crop Specimens from Trays
    crop_specimens_from_trays(trays_dir, resized_trays_dir, specimens_dir)

if __name__ == '__main__':
    main()
