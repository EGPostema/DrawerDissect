from PIL import Image, ImageFile
import os
import time
from multiprocessing import Pool, cpu_count

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def resize_image(args):
    input_path, output_dir = args
    
    try:
        filename = os.path.basename(input_path)
        
        # Add _1000 suffix before the file extension
        base_name, ext = os.path.splitext(filename)
        output_filename = f"{base_name}_1000{ext}"
        output_path = os.path.join(output_dir, output_filename)
        
        if os.path.exists(output_path):
            print(f"Skipping {filename}, already resized.")
            return
        
        with Image.open(input_path) as img:
            new_width = 1000
            new_height = int(img.height * (1000 / img.width))
            img_resized = img.resize((new_width, new_height))
            img_resized.save(output_path)
            print(f"Resized {filename} and saved to {output_path}")
    except Exception as e:
        print(f"Error processing {filename}: {e}")

def resize_drawer_images(input_dir, output_dir):
    start_time = time.time()  # Start the timer
    
    # Get list of .jpg files in the input directory
    file_paths = [os.path.join(input_dir, filename) for filename in os.listdir(input_dir) if filename.endswith('.jpg')]
    
    # Prepare arguments for multiprocessing
    args = [(file_path, output_dir) for file_path in file_paths]
    
    # Use multiprocessing Pool to resize images in parallel
    with Pool(cpu_count()) as pool:
        pool.map(resize_image, args)
    
    elapsed_time = time.time() - start_time
    print(f"Drawer resizing complete. Total time: {elapsed_time:.2f} seconds.")