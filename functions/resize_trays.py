from PIL import Image, ImageFile
import os
import time
from multiprocessing import Pool, cpu_count

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def resize_image(args):
    input_path, output_dir, new_width, input_dir = args
    try:
        filename = os.path.basename(input_path)
        root = os.path.dirname(input_path)
        base_name = os.path.splitext(filename)[0]
        original_ext = os.path.splitext(filename)[1]

        relative_path = os.path.relpath(root, input_dir)
        output_subdir = os.path.join(output_dir, relative_path)
        os.makedirs(output_subdir, exist_ok=True)
        
        output_filename = f"{base_name}_1000.jpg"  # Always output as JPG
        output_path = os.path.join(output_subdir, output_filename)

        if os.path.exists(output_path):
            print(f"Skipping {filename}, already resized.")
            return

        with Image.open(input_path) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGB')
            new_height = int((new_width / img.width) * img.height)
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            resized_img.save(output_path, quality=95)
            print(f"Resized {filename} and saved to {output_path}")
    except Exception as e:
        print(f"Error resizing {filename}: {e}")

def resize_tray_images(input_dir, output_dir, new_width=1000):
    start_time = time.time()
    
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    file_paths = []
    
    for root, dirs, files in os.walk(input_dir):
        for filename in files:
            full_path = os.path.join(root, filename)
            if filename.lower().endswith(supported_formats):
                file_paths.append(full_path)
    
    print(f"Total images found: {len(file_paths)}")
    
    args = [(file_path, output_dir, new_width, input_dir) for file_path in file_paths]
    with Pool(cpu_count()) as pool:
        pool.map(resize_image, args)
    print(f"Tray resizing complete. Total time: {time.time() - start_time:.2f} seconds.")





