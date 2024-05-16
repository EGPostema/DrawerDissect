from PIL import Image, ImageFile
import os

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def resize_tray_images(input_dir, output_dir, new_width=1000):
    for filename in os.listdir(input_dir):
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        with Image.open(input_path) as img:
            new_height = int((new_width / img.width) * img.height)
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            resized_img.save(output_path)

if __name__ == '__main__':
    resize_tray_images('data/drawers/trays', 'data/drawers/resized_trays')

