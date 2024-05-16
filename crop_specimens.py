import os
import json
from PIL import Image

def crop_specimens_from_trays(trays_dir, resized_trays_dir, specimens_dir):
    for root, _, files in os.walk(resized_trays_dir):
        for file in files:
            if file.endswith(".json"):
                json_path = os.path.join(root, file)
                with open(json_path) as json_file:
                    annotations = json.load(json_file)
                    image_filename = annotations['image']['file_name']
                    original_path = os.path.join(trays_dir, image_filename)
                    resized_path = os.path.join(resized_trays_dir, image_filename)
                    crop_images_based_on_bboxes(original_path, resized_path, annotations['predictions'], specimens_dir)

def crop_images_based_on_bboxes(original_path, resized_path, bboxes, output_folder):
    with Image.open(original_path) as orig_img, Image.open(resized_path) as resized_img:
        scale_x = orig_img.width / resized_img.width
        scale_y = orig_img.height / resized_img.height
        buffer = 50  # 50px buffer

        for i, bbox in enumerate(bboxes):
            x, y, width, height = bbox['bbox']
            x1 = int((x - buffer) * scale_x)
            y1 = int((y - buffer) * scale_y)
            x2 = int((x + width + buffer) * scale_x)
            y2 = int((y + height + buffer) * scale_y)
            cropped_img = orig_img.crop((x1, y1, x2, y2))
            crop_filename = f"{os.path.basename(original_path).split('.')[0]}_specimen_{i+1}.jpg"
            cropped_img.save(os.path.join(output_folder, crop_filename))

if __name__ == '__main__':
    crop_specimens_from_trays('data/drawers/trays', 'data/drawers/resized_trays', 'data/drawers/specimens')


