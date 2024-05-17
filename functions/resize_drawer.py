from PIL import Image, ImageFile
import os

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def resize_drawer_images(input_dir, output_dir):
    for filename in os.listdir(input_dir):
        if filename.endswith('.jpg'):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename.replace('.jpg', '_1000.jpg'))
            
            if os.path.exists(output_path):
                print(f"Skipping {filename}, already resized.")
                continue
            
            with Image.open(input_path) as img:
                img_resized = img.resize((1000, int(img.height * (1000 / img.width))))
                img_resized.save(output_path)
                print(f"Resized {filename} and saved to {output_path}")
