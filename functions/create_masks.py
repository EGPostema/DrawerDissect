import os
import json
import csv
import numpy as np
from PIL import Image, ImageDraw
from multiprocessing import Pool, cpu_count

def process_mask(args):
    json_path, csv_path, png_path = args

    try:
        with open(json_path, 'r') as json_file:
            data = json.load(json_file)

        image_info = data.get('image', {})
        img_width = int(image_info.get('width', 0))
        img_height = int(image_info.get('height', 0))

        for prediction in data.get('predictions', []):
            # Skip if width or height is missing
            if img_width == 0 or img_height == 0:
                print(f"Skipping {json_path} due to missing width/height.")
                continue

            # Create ImageDraw object
            binary_mask = Image.new('L', (img_width, img_height))
            draw = ImageDraw.Draw(binary_mask)

            points = prediction.get('points', [])
            xy = [(int(point['x']), int(point['y'])) for point in points]

            # Fill the polygon in binary_mask
            draw.polygon(xy, outline=0, fill=255)

            # Convert binary_mask to numpy array
            mask_array = np.array(binary_mask)

            # Ensure mask_array contains only 0s and 1s
            mask_array[mask_array > 0] = 1

            # Save binary mask image
            binary_mask.save(png_path)

            # Write mask data to CSV
            with open(csv_path, 'w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                rows = mask_array.tolist()
                for row in rows:
                    csv_writer.writerow(row)

        print(f"Converted {json_path} to binary mask {png_path}")
    except Exception as e:
        print(f"Error converting {json_path}: {e}")

def create_masks(jsondir, csvdir, pngdir):
    os.makedirs(csvdir, exist_ok=True)
    os.makedirs(pngdir, exist_ok=True)

    tasks = []
    for root, _, files in os.walk(jsondir):
        for file in files:
            if file.endswith('.json'):
                json_path = os.path.join(root, file)
                relative_path = os.path.relpath(json_path, jsondir)
                csv_path = os.path.join(csvdir, relative_path.replace('.json', '.csv'))
                png_path = os.path.join(pngdir, relative_path.replace('.json', '.png'))

                # Skip if the CSV or PNG already exists
                if os.path.exists(csv_path) and os.path.exists(png_path):
                    print(f"Skipping {json_path} because corresponding .csv and .png already exist.")
                    continue

                os.makedirs(os.path.dirname(csv_path), exist_ok=True)
                os.makedirs(os.path.dirname(png_path), exist_ok=True)

                tasks.append((json_path, csv_path, png_path))

    # Use multiprocessing to process images in parallel
    with Pool(cpu_count()) as pool:
        pool.map(process_mask, tasks)




