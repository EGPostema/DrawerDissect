import cv2
import numpy as np
import os
import csv
from concurrent.futures import ProcessPoolExecutor

def measure_mask(image_path, input_folder):
    print(f"Processing image: {image_path}")
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        print(f"Failed to read image: {image_path}")
        return [None, None, None, os.path.basename(image_path), None, None, None, None, None]  # Added placeholders for image dimensions
    
    image_height, image_width = image.shape  # Get image dimensions
    _, thresholded = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
    
    contours, _ = cv2.findContours(thresholded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        print(f"No contours found in image: {image_path}")
        return [None, None, None, os.path.basename(image_path), None, None, None, image_height, image_width]  # Added image dimensions
    
    contour = max(contours, key=cv2.contourArea)
    
    rect = cv2.minAreaRect(contour)
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    
    width = np.linalg.norm(box[0] - box[1])
    height = np.linalg.norm(box[1] - box[2])
    
    area = cv2.contourArea(contour)
    
    length1 = max(width, height)
    length2 = min(width, height)
    
    # Extract necessary identifiers from image path
    img_name = os.path.basename(image_path)
    full_id = os.path.splitext(img_name)[0]
    drawer_id = full_id.split('_tray')[0]
    tray_id = full_id.split('_spec')[0]
    
    return [full_id, tray_id, drawer_id, img_name, length1, length2, area, image_height, image_width]

def write_lengths(input_folder, output_csv):
    print(f"Starting to process images in folder: {input_folder}")
    if not os.path.exists(input_folder):
        print(f"Input folder does not exist: {input_folder}")
        return
    if not any(file.endswith('.png') for root, _, files in os.walk(input_folder) for file in files):
        print(f"No PNG files found in input folder: {input_folder}")
        return
    
    data = []
    with ProcessPoolExecutor() as executor:
        futures = []
        for root, _, files in os.walk(input_folder):
            print(f"Scanning directory: {root}")
            for filename in files:
                if filename.endswith('.png'):
                    image_path = os.path.join(root, filename)
                    print(f"Found image file: {image_path}")
                    futures.append(executor.submit(measure_mask, image_path, input_folder))
        
        for future in futures:
            try:
                result = future.result()
                if result:
                    print(f"Processed result: {result}")
                    data.append(result)
            except Exception as e:
                print(f"Error processing image: {e}")
    
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["full_id", "tray_id", "drawer_id", "spec_filename", "length1", "length2", "area_px", "img_height", "img_width"])  # Added extension to the header
        writer.writerows(data)
    
    print(f"Completed processing. Results saved to {output_csv}")