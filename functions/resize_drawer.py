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
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_1000.jpg"
        output_path = os.path.join(output_dir, output_filename)
        
        if output_filename in completed_files:
            print(f"Skipping {filename}, already resized.")
            return
        
        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGB')
                
            scale_factor = min(1000 / img.width, 1000 / img.height)
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)
            
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            img_resized.save(output_path, quality=95)
            print(f"Resized {filename} and saved to {output_path}")
    except Exception as e:
        print(f"Error processing {filename}: {e}")

def resize_drawer_images(input_dir, output_dir):
    start_time = time.time()  # Start the timer
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    file_paths = [
        os.path.join(input_dir, filename) 
        for filename in os.listdir(input_dir) 
        if filename.lower().endswith(supported_formats)
    ]
    
    completed_files = set(os.listdir(output_dir))
    args = [(file_path, output_dir, completed_files) for file_path in file_paths]
    
    with Pool(cpu_count()) as pool:
        pool.map(resize_image, args)

    elapsed_time = time.time() - start_time
    print(f"Drawer resizing complete. Total time: {elapsed_time:.2f} seconds.")


