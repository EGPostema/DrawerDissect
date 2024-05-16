from PIL import Image, ImageFile
import os

# Adjust the max image pixels limit
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def resize_image(input_path, output_path, new_width):
    with Image.open(input_path) as img:
        new_height = int((new_width / img.width) * img.height)
        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        resized_img.save(output_path)
    return output_path

def resize_drawers():
    original_dir = 'drawers/fullsize'
    resized_dir = 'drawers/resized'
    os.makedirs(resized_dir, exist_ok=True)
    for filename in os.listdir(original_dir):
        if filename.endswith('.jpg'):
            original_image_path = os.path.join(original_dir, filename)
            output_image_path = os.path.join(resized_dir, filename.replace('.jpg', '_1000.jpg'))
            if not os.path.exists(output_image_path):
                resize_image(original_image_path, output_image_path, 1000)
            else:
                print(f"Skipping {filename}: already resized.")
    print("All images have been resized to 1000 pixels wide and saved in the 'resized' directory.")
