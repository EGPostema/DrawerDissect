import os
import json
import csv
import numpy as np
from PIL import Image, ImageDraw

def json_to_csv(jsondir, csvdir):
    os.makedirs(csvdir, exist_ok=True)

    for root, _, files in os.walk(jsondir):
        for file in files:
            json_path = os.path.join(root, file)
            csv_path = os.path.join(csvdir, file.replace('.json', '.csv'))
            mask_path = os.path.join(csvdir, file.replace('.json', '.png'))

            with open(json_path, 'r') as json_file:
                data = json.load(json_file)

            try:
                for prediction in data.get('predictions', []):
                    width = int(prediction.get('width', 5000)*2)
                    height = int(prediction.get('height', 5000)*1.5)

                    # Create ImageDraw object
                    binary_mask = Image.new('L', (width, height))
                    draw = ImageDraw.Draw(binary_mask)

                    mask_array = np.zeros((height, width), dtype=np.uint8)

                    points = prediction.get('points', [])

                    xy = [(int(point['x']), int(point['y'])) for point in points]

                    # Fill the polygon in binary_mask
                    draw.polygon(xy, outline=0, fill=255)

                    # Convert binary_mask to numpy array
                    mask_array = np.array(binary_mask)

                    # Ensure mask_array contains only 0s and 1s
                    mask_array[mask_array > 0] = 1

                    # Save binary mask image
                    binary_mask.save(mask_path)

                    # Write mask data to CSV
                    with open(csv_path, 'w', newline='') as csv_file:
                        csv_writer = csv.writer(csv_file)
                        rows = mask_array.tolist()
                        for row in rows:
                            csv_writer.writerow(row)

                    print(f"Converted {json_path} to binary mask {mask_path}")

            except Exception as e:
                print(f"Error converting {json_path}: {e}")
