from PIL import Image, ImageFile
import os
import time
from multiprocessing import Pool, cpu_count

# Allow processing of large images
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def resize_image(args):
    input_path, output_dir, completed_files = args
    
    try:
        filename = os.path.basename(input_path)
        
        # Split the filename to extract the part before the timestamp
        base_name, ext = os.path.splitext(filename)
        base_name_without_timestamp = base_name.rsplit('_', 2)[0]  # Keep the part before the last three underscores
        
        # Add _1000 suffix before the file extension
        output_filename = f"{base_name_without_timestamp}_1000{ext}"
        output_path = os.path.join(output_dir, output_filename)
        
        # Check if this file has already been resized by comparing the output filename
        if output_filename in completed_files:
            print(f"Skipping {filename}, already resized.")
            return
        
        # Open the image
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
    
    # Collect completed files in the output directory
    completed_files = set(os.listdir(output_dir))
    
    # Prepare arguments for multiprocessing
    args = [(file_path, output_dir, completed_files) for file_path in file_paths]
    
    # Use multiprocessing Pool to resize images in parallel
    with Pool(cpu_count()) as pool:
        pool.map(resize_image, args)
    
    elapsed_time = time.time() - start_time
    print(f"Drawer resizing complete. Total time: {elapsed_time:.2f} seconds.")


