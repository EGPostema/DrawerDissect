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
        
        # Simply get the base name without extension
        base_name = os.path.splitext(filename)[0]
        
        # Add _1000 suffix for the resized image
        output_filename = f"{base_name}_1000.jpg"
        output_path = os.path.join(output_dir, output_filename)
        
        # Check if this file has already been resized
        if output_filename in completed_files:
            print(f"Skipping {filename}, already resized.")
            return
        
        # Open the image
        with Image.open(input_path) as img:
            # Calculate the scaling factor to fit within 1000x1000 while maintaining aspect ratio
            scale_factor = min(1000 / img.width, 1000 / img.height)
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)
            
            # Resize the image
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
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



