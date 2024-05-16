# Import necessary libraries
from PIL import Image, ImageFile
import os

# Adjust the max image pixels limit
Image.MAX_IMAGE_PIXELS = None  # Remove the limit entirely
ImageFile.LOAD_TRUNCATED_IMAGES = True  # Allow loading of truncated images

# Function to resize images
def resize_image(input_path, output_path, new_width):
    with Image.open(input_path) as img:
        # Calculate the new height to maintain aspect ratio
        new_height = int((new_width / img.width) * img.height)
        
        # Resize the image
        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Save the resized image
        resized_img.save(output_path)
    return output_path

# Directory paths
trays_dir = 'trays'
resized_trays_dir = 'resized_trays'

# Ensure the resized_trays directory exists
os.makedirs(resized_trays_dir, exist_ok=True)

# Walk through the directory tree of trays
for root, dirs, files in os.walk(trays_dir):
    for filename in files:
        if filename.endswith('.jpg'):
            # Construct full file paths
            original_image_path = os.path.join(root, filename)
            
            # Determine the relative subfolder path
            relative_subfolder = os.path.relpath(root, trays_dir)
            
            # Construct the corresponding output path in resized_trays
            output_subfolder_path = os.path.join(resized_trays_dir, relative_subfolder)
            os.makedirs(output_subfolder_path, exist_ok=True)
            
            # Construct the output image path
            resized_image_path = os.path.join(output_subfolder_path, filename.replace('.jpg', '_1000.jpg'))
            
            # Resize images to 1000 pixels wide
            resize_image(original_image_path, resized_image_path, 1000)

print("All images have been resized to 1000 pixels wide and saved in the 'resized_trays' directory.")
