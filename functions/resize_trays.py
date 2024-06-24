from PIL import Image, ImageFile
import os
import time

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def resize_tray_images(input_dir, output_dir, new_width=1000):
    start_time = time.time()  # Start the timer
    
    for filename in os.listdir(input_dir):
        if filename.endswith('.jpg'):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename.replace('.jpg', '_1000.jpg'))

            if os.path.exists(output_path):
                print(f"Skipping {filename}, already resized.")
                continue

            try:
                with Image.open(input_path) as img:
                    new_height = int((new_width / img.width) * img.height)
                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                    resized_img.save(output_path)
                    print(f"Resized {filename} and saved to {output_path}")
            except Exception as e:
                print(f"Error resizing {filename}: {e}")
                
    elapsed_time = time.time() - start_time
    print(f"Tray resizing complete. Total time: {elapsed_time:.2f} seconds.")


