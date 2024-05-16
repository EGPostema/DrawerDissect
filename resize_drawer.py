# RESIZE DRAWER TO 1000PX WIDE MAX

from PIL import Image, ImageFile
import os

# Adjust the max image pixels limit
Image.MAX_IMAGE_PIXELS = None  # Remove the limit entirely
ImageFile.LOAD_TRUNCATED_IMAGES = True  # Allow loading of truncated images

def resize_image(input_path, output_path, new_width):
    with Image.open(input_path) as img:
        # Calculate the new height to maintain aspect ratio
        new_height = int((new_width / img.width) * img.height)
        
        # Resize the image
        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Save the resized image
        resized_img.save(output_path)
    return output_path

# Directory paths adjusted for the current working directory
original_dir = 'fullsize'
resized_dir = 'resized'

# Create the resized directory if it doesn't exist
os.makedirs(resized_dir, exist_ok=True)

# Iterate over all JPEG files in the original directory
for filename in os.listdir(original_dir):
    if filename.endswith('.jpg'):
        original_image_path = os.path.join(original_dir, filename)
        output_image_path = os.path.join(resized_dir, filename.replace('.jpg', '_1000.jpg'))

        # Check if the resized image already exists
        if not os.path.exists(output_image_path):
            # Resize the image to 1000 pixels wide
            resize_image(original_image_path, output_image_path, 1000)
        else:
            print(f"Skipping {filename}: already resized.")

print("All images have been resized to 1000 pixels wide and saved in the 'resized' directory.")
