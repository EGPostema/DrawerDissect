from PIL import Image, ImageFile
import os
import time

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def resize_drawer_images(input_dir, output_dir):
    
    start_time = time.time()  # Start the timer
    
    for filename in os.listdir(input_dir):
        if filename.endswith('.jpg'):
            input_path = os.path.join(input_dir, filename)

            # Extract the desired part of the filename and add _1000 suffix
            base_name = '_'.join(filename.split('_')[:3])
            output_filename = f"{base_name}_1000.jpg"
            output_path = os.path.join(output_dir, output_filename)
            
            if os.path.exists(output_path):
                print(f"Skipping {filename}, already resized.")
                continue
            
            with Image.open(input_path) as img:
                img_resized = img.resize((1000, int(img.height * (1000 / img.width))))
                img_resized.save(output_path)
                print(f"Resized {filename} and saved to {output_path}")

    end_time = time.time()  # End the timer
    elapsed_time = end_time - start_time
    print(f"Drawer resizing complete. Total time: {elapsed_time:.2f} seconds.")
