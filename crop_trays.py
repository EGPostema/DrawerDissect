import os
import json
from PIL import Image, ImageFile

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def crop_trays_from_fullsize(fullsize_dir, resized_dir, trays_dir):
    json_file_path = os.path.join(resized_dir, 'coordinates', '_annotations.coco.json')
    with open(json_file_path) as json_file:
        annotations = json.load(json_file)
    
    for annotation in annotations:
        original_path = os.path.join(fullsize_dir, annotation['file_name'])
        resized_path = os.path.join(resized_dir, annotation['file_name'])
        crop_images_based_on_bboxes(original_path, resized_path, annotation['bboxes'], trays_dir)

def crop_images_based_on_bboxes(original_path, resized_path, bboxes, output_folder):
    with Image.open(original_path) as orig_img, Image.open(resized_path) as resized_img:
        scale_x = orig_img.width / resized_img.width
        scale_y = orig_img.height / resized_img.height
        buffer = 50  # 50px buffer

        for i, bbox in enumerate(bboxes):
            x, y, width, height = bbox
            x1 = int((x - buffer) * scale_x)
            y1 = int((y - buffer) * scale_y)
            x2 = int((x + width + buffer) * scale_x)
            y2 = int((y + height + buffer) * scale_y)
            cropped_img = orig_img.crop((x1, y1, x2, y2))
            crop_filename = f"{os.path.basename(original_path).split('.')[0]}_tray_{i+1}.jpg"
            cropped_img.save(os.path.join(output_folder, crop_filename))

if __name__ == '__main__':
    crop_trays_from_fullsize('data/drawers/fullsize', 'data/drawers/resized', 'data/drawers/trays')

