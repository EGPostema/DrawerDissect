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
                
            try:
                with Image.open(input_path) as img:
                    new_width = 1000
                    new_height = int(img.height * (1000 / img.width))
                    img_resized = img.resize((new_width, new_height))
                    img_resized.save(output_path)
                    print(f"Resized {filename} and saved to {output_path}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    
    elapsed_time = time.time() - start_time
    print(f"Drawer resizing complete. Total time: {elapsed_time:.2f} seconds.")
