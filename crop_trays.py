import os
import json
from PIL import Image, ImageFile

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def crop_trays(original_path, resized_path, coordinates_path, output_folder):
    with Image.open(original_path) as orig_img:
        with Image.open(resized_path) as resized_img:
            scale_x = orig_img.width / resized_img.width
            scale_y = orig_img.height / resized_img.height
            with open(coordinates_path, 'r') as file:
                data = json.load(file)
            for i, annotation in enumerate(data['annotations'], 1):
                bbox = annotation['bbox']
                xmin = max(int(bbox[0] * scale_x), 0)
                ymin = max(int(bbox[1] * scale_y), 0)
                xmax = min(int((bbox[0] + bbox[2]) * scale_x), orig_img.width)
                ymax = min(int((bbox[1] + bbox[3]) * scale_y), orig_img.height)
                if xmax > xmin and ymax > ymin:
                    cropped_img = orig_img.crop((xmin, ymin, xmax, ymax))
                    output_path = os.path.join(output_folder, f"{os.path.splitext(os.path.basename(original_path))[0]}_tray_{i:03}.jpg")
                    cropped_img.save(output_path)

def crop_trays_from_coordinates():
    coordinates_dir = 'drawers/resized/coordinates'
    resized_dir = 'drawers/resized'
    fullsize_dir = 'drawers/fullsize'
    trays_dir = 'drawers/trays'
    os.makedirs(trays_dir, exist_ok=True)
    for json_filename in os.listdir(coordinates_dir):
        json_path = os.path.join(coordinates_dir, json_filename)
        with open(json_path, 'r') as file:
            data = json.load(file)
        image_filename = data['images'][0]['file_name']
        resized_image_path = os.path.join(resized_dir, image_filename)
        original_image_path = os.path.join(fullsize_dir, image_filename.replace('_1000', ''))
        if os.path.exists(original_image_path) and os.path.exists(resized_image_path):
            crop_trays(original_image_path, resized_image_path, json_path, trays_dir)
    print("Processing complete. Trays cropped and saved in the 'drawers/trays' directory.")

if __name__ == "__main__":
    crop_trays_from_coordinates()
