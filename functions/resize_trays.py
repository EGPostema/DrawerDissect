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

        # Recreate the subfolder structure in the output directory
        relative_path = os.path.relpath(root, input_dir)
        output_subdir = os.path.join(output_dir, relative_path)
        os.makedirs(output_subdir, exist_ok=True)
        
        output_filename = filename.replace('.jpg', '_1000.jpg')
        output_path = os.path.join(output_subdir, output_filename)

        if os.path.exists(output_path):
            print(f"Skipping {filename}, already resized.")
            return

        with Image.open(input_path) as img:
            new_height = int((new_width / img.width) * img.height)
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            resized_img.save(output_path)
            print(f"Resized {filename} and saved to {output_path}")
    except Exception as e:
        print(f"Error resizing {filename}: {e}")

def resize_tray_images(input_dir, output_dir, new_width=1000):
    start_time = time.time()  # Start the timer

    # Get list of .jpg files in the input directory
    file_paths = []
    for root, _, files in os.walk(input_dir):
        for filename in files:
            if filename.endswith('.jpg'):
                file_paths.append(os.path.join(root, filename))

    # Prepare arguments for multiprocessing
    args = [(file_path, output_dir, new_width, input_dir) for file_path in file_paths]

    # Use multiprocessing Pool to resize images in parallel
    with Pool(cpu_count()) as pool:
        pool.map(resize_image, args)

    elapsed_time = time.time() - start_time
    print(f"Tray resizing complete. Total time: {elapsed_time:.2f} seconds.")





