import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import csv
from multiprocessing import Pool, cpu_count

# Function to check if the _dimensions.png file already exists
def image_already_processed(output_path):
    return os.path.exists(output_path)

# Function to process a single image and calculate the longest dimension and area
def process_image(file_path, output_path):
    # Load the mask image as grayscale
    mask_image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
    
    if mask_image is None:
        print(f"Error loading {file_path}. Skipping.")
        return None, None, None
    
    # Threshold the image to binary
    _, binary = cv2.threshold(mask_image, 127, 255, cv2.THRESH_BINARY)
    
    # Find contours of the white area
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        print(f"No contours found in {file_path}.")
        return None, None, None

    contour = max(contours, key=cv2.contourArea)

    # Function to calculate the longest dimension based on farthest points
    def calculate_longest_dimension(image_contour):
        max_distance = 0
        point1, point2 = None, None
        for i in range(len(image_contour)):
            for j in range(i + 1, len(image_contour)):
                dist = np.linalg.norm(image_contour[i][0] - image_contour[j][0])
                if dist > max_distance:
                    max_distance = dist
                    point1, point2 = image_contour[i][0], image_contour[j][0]
        return max_distance, point1, point2

    # Calculate the longest dimension and the farthest points
    longest_dimension, p1, p2 = calculate_longest_dimension(contour)

    # Compute the area of the white part
    area_px = cv2.contourArea(contour)

    # Calculate the centroid of the object
    M = cv2.moments(contour)
    if M["m00"] != 0:
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
    else:
        cX, cY = 0, 0

    # Create and save the visual
    plt.figure(figsize=(6, 6))
    plt.imshow(binary, cmap='gray')

    # Plot the contour
    plt.plot(contour[:, 0, 0], contour[:, 0, 1], color='blue', label='Contour')

    # Plot the longest distance line and points
    plt.plot([p1[0], p2[0]], [p1[1], p2[1]], 'g--', label=f'Longest Dimension: {longest_dimension:.2f} pixels')
    plt.scatter([p1[0], p2[0]], [p1[1], p2[1]], color='yellow', label='Max Distance Points')

    # Plot the centroid on the visual
    plt.scatter(cX, cY, color='red', label='Centroid', marker='x')

    # Move the legend below the plot
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1))
    plt.title(f'Longest Dimension: {longest_dimension:.2f} pixels')
    plt.grid(True)

    # Save the visual
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()

    # Determine if the size is bad
    bad_size = "Y" if longest_dimension < 900 else "N"

    return longest_dimension, area_px, bad_size

# Function to handle the image processing for a single file
def process_file(file_info):
    """Wrapper to process a single file with multiprocessing."""
    file_path, output_image_path = file_info
    if image_already_processed(output_image_path):
        print(f"Skipping {file_path} as it is already processed.")
        return None
    longest_px, area_px, bad_size = process_image(file_path, output_image_path)
    if longest_px is None:
        return None
    full_id = os.path.splitext(os.path.basename(file_path))[0]
    return [full_id, longest_px, area_px, bad_size]

# Main function to process images
def process_and_measure_images(mask_png_dir, output_csv, output_visual_dir):
    # Main image processing logic
    file_info_list = []

    # Traverse the directory and get all .png files
    for root, _, files in os.walk(mask_png_dir):
        for file in files:
            if file.endswith(".png"):  # Process only .png files
                file_path = os.path.join(root, file)
                filename = os.path.splitext(file)[0]  # Get the filename without extension
                relative_path = os.path.relpath(root, mask_png_dir)  # Mirror subfolder structure
                
                output_image_path = os.path.join(output_visual_dir, relative_path, f"{filename}_dimensions.png")
                file_info_list.append((file_path, output_image_path))

    # Use multiprocessing to process the files
    with Pool(cpu_count()) as pool:
        results = pool.map(process_file, file_info_list)

    # Filter out any skipped files
    results = [result for result in results if result is not None]

    # Write results to CSV
    with open(output_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['full_id', 'longest_px', 'area_px', 'bad_size'])
        writer.writerows(results)
