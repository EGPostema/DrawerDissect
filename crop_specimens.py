import os
import json
from PIL import Image

# Directory setup
resized_trays_dir = 'resized_trays'
trays_dir = 'trays'
coordinates_dir = os.path.join(resized_trays_dir, 'coordinates')
specimens_dir = 'specimens'

# Ensure the specimens directory exists
os.makedirs(specimens_dir, exist_ok=True)

def crop_images_based_on_bboxes(original_path, resized_path, annotations, output_folder):
    with Image.open(original_path) as orig_img, Image.open(resized_path) as resized_img:
        scale_x = orig_img.width / resized_img.width
        scale_y = orig_img.height / resized_img.height
        
        buffer = 50  # 50px buffer

        for i, annotation in enumerate(annotations, 1):
            bbox = annotation['bbox']
            xmin = max(int((bbox[0] * scale_x) - buffer), 0)
            xmax = min(int((bbox[0] + bbox[2]) * scale_x) + buffer, orig_img.width)
            ymin = max(int((bbox[1] * scale_y) - buffer), 0)
            ymax = min(int((bbox[1] + bbox[3]) * scale_y) + buffer, orig_img.height)

            # Only crop if the bounding box is valid
            if xmax > xmin and ymax > ymin:
                cropped_img = orig_img.crop((xmin, ymin, xmax, ymax))
                cropped_image_path = os.path.join(output_folder, f'{os.path.splitext(os.path.basename(original_path))[0]}_spec_{i:03}.jpg')
                cropped_img.save(cropped_image_path)

# Read and process each JSON file
for json_filename in os.listdir(coordinates_dir):
    json_path = os.path.join(coordinates_dir, json_filename)
    with open(json_path, 'r') as file:
        data = json.load(file)

    # Process each image referenced in the JSON file
    for image_info in data['images']:
        base_name = image_info['file_name'].split('.')[0]  # Get base name without extension and extra details
        resized_image_name = f"{base_name}_1000.jpg"
        original_image_name = f"{base_name.replace('_1000', '')}.jpg"

        resized_image_path = os.path.join(resized_trays_dir, resized_image_name)
        original_image_path = os.path.join(trays_dir, original_image_name)
        
        # Check if both the resized and original images exist
        if os.path.exists(resized_image_path) and os.path.exists(original_image_path):
            annotations = [ann for ann in data['annotations'] if ann['image_id'] == image_info['id']]
            crop_images_based_on_bboxes(original_image_path, resized_image_path, annotations, specimens_dir)

print("Processing complete. Images cropped and saved in the 'specimens' directory.")

