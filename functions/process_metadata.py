import os
import re
import pandas as pd
from PIL import Image, ImageFile
from multiprocessing import Pool, cpu_count
from datetime import datetime
from typing import Optional, Tuple

# Allow opening very large images
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def parse_metadata(metadata_path):
    """Parse metadata file for image dimensions and properties."""
    with open(metadata_path, 'r') as file:
        data = file.read()
    
    metadata = {}
    try:
        metadata['project_total'] = int(re.search(r'"project_total":"(\d+)"', data).group(1))
        metadata['project_image_overlap'] = float(re.search(r'"project_image_overlap":"([\d\.]+)"', data).group(1))
        metadata['project_image_overlap_vertical'] = float(re.search(r'"project_image_overlap_vertical":"([\d\.]+)"', data).group(1))
        metadata['project_columns'] = int(re.search(r'"project_columns":"(\d+)"', data).group(1))
        metadata['project_rows'] = int(re.search(r'"project_rows":"(\d+)"', data).group(1))
    except AttributeError as e:
        raise ValueError(f"Metadata parsing error in {metadata_path}: {e}")
    
    return metadata

def calculate_dimensions(metadata, fov_width=77.75, fov_height=51.83):
    """Calculate total dimensions based on metadata and FOV."""
    horizontal_overlap = metadata['project_image_overlap']
    vertical_overlap = metadata['project_image_overlap_vertical']
    columns = metadata['project_columns']
    rows = metadata['project_rows']
    
    effective_fov_width = fov_width * (1 - horizontal_overlap)
    effective_fov_height = fov_height * (1 - vertical_overlap)
    
    total_width_mm = (columns - 1) * effective_fov_width + fov_width
    total_height_mm = (rows - 1) * effective_fov_height + fov_height
    
    return total_width_mm, total_height_mm

def parse_drawer_filename(filename: str) -> Optional[Tuple[str, str]]:
    """
    Parse a drawer filename to extract drawer_id.
    Expected format: {drawer_id}_MM-DD-YYYY_HH_MM_TT.{extension}
    
    Args:
        filename: String filename to parse
        
    Returns:
        Tuple of (drawer_id, timestamp_str) if valid, None if invalid
    """
    try:
        base = filename.rsplit('.', 1)[0]  # Remove extension
        drawer_id = '_'.join(base.split('_')[:-1])  # Everything before the timestamp
        timestamp = base.split('_')[-1]  # The timestamp portion
        return (drawer_id, timestamp)
    except IndexError:
        return None

def find_matching_files(metadata_dir: str, image_dir: str) -> list[tuple[str, str]]:
    """
    Find matching pairs of image and metadata files.
    """
    metadata_files = {f for f in os.listdir(metadata_dir) if f.endswith('.txt')}
    image_files = {f for f in os.listdir(image_dir) if f.endswith('.jpg')}
    
    print(f"\nFound {len(metadata_files)} metadata files and {len(image_files)} image files")
    
    # Create metadata lookup
    metadata_lookup = {}
    for f in metadata_files:
        if f.startswith('capture_metadata_'):
            # Remove 'capture_metadata_' and '.txt', and any leading underscore
            timestamp = f[16:].replace('.txt', '').lstrip('_')
            print(f"From metadata '{f}' got timestamp: '{timestamp}'")
            metadata_lookup[timestamp] = f
    
    print(f"\nExtracted {len(metadata_lookup)} timestamps from metadata files")
    
    # Find matching image files
    matches = []
    for img in image_files:
        try:
            # Get the date and time parts (last two underscore-separated segments)
            parts = img.split('_')
            timestamp = f"{parts[-2]}_{parts[-1].replace('.jpg', '')}"
            print(f"\nFrom image '{img}' got timestamp: '{timestamp}'")
            
            if timestamp in metadata_lookup:
                metadata_file = metadata_lookup[timestamp]
                print(f"MATCH! Image: {img} -> Metadata: {metadata_file}")
                matches.append((
                    os.path.join(metadata_dir, metadata_file),
                    os.path.join(image_dir, img)
                ))
            else:
                print(f"No match for timestamp: {timestamp}")
                print("Available timestamps:", list(metadata_lookup.keys())[:3])
        except IndexError:
            print(f"Could not parse timestamp from image: {img}")
            continue
    
    print(f"\nFound {len(matches)} matching pairs")
    if matches:
        print("First match:", matches[0])
    
    return matches

def process_files(metadata_dir: str, image_dir: str, output_file: str):
    """Process all matching image and metadata files to calculate dimensions."""
    if not os.path.exists(metadata_dir) or not os.path.exists(image_dir):
        raise FileNotFoundError("Metadata or image directory does not exist. Please check the paths.")
    
    # Find all matching pairs of files
    file_pairs = find_matching_files(metadata_dir, image_dir)
    
    if not file_pairs:
        print("No matching file pairs found. Exiting...")
        return
        
    results = []
    for metadata_path, image_path in file_pairs:
        try:
            metadata = parse_metadata(metadata_path)
            
            with Image.open(image_path) as img:
                width_px, height_px = img.size
            
            width_mm, height_mm = calculate_dimensions(metadata)
            width_ratio = width_px / width_mm
            height_ratio = height_px / height_mm
            pixel_to_mm_ratio = round((width_ratio + height_ratio) / 2, 2)
            
            # Extract drawer_id from the filename
            drawer_info = parse_drawer_filename(os.path.basename(image_path))
            if drawer_info is None:
                print(f"Warning: Could not parse drawer ID from {image_path}")
                continue
            drawer_name = drawer_info[0]
            
            results.append({
                'drawer_id': drawer_name,
                'image_height_mm': round(height_mm, 2),
                'image_width_mm': round(width_mm, 2),
                'image_height_px': height_px,
                'image_width_px': width_px,
                'px_mm_ratio': pixel_to_mm_ratio
            })
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            continue
    
    if not results:
        print("No valid results found. Exiting...")
        return
        
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")

