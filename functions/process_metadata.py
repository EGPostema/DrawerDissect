import os
import re
import pandas as pd
from PIL import Image, ImageFile
from typing import Optional, List, Tuple
from logging_utils import log, log_found, log_progress

# Allow opening very large images
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def extract_project_name(metadata_path: str) -> Optional[str]:
    """
    Extract project name from metadata file and format it to match image filenames.
    Converts "34 4 6" to "34_4_6"
    """
    try:
        with open(metadata_path, 'rb') as file:
            data = file.read(1024).decode('utf-8')
        
        project_name_match = re.search(r'"project_name":"([^"]+)"', data)
        if not project_name_match:
            log(f"Error: No project name found in {metadata_path}")
            return None
            
        # Convert spaces to underscores
        project_name = project_name_match.group(1)
        formatted_name = '_'.join(project_name.split())
        log(f"Extracted project name: {project_name} -> {formatted_name}")
        return formatted_name
        
    except Exception as e:
        log(f"Error: Failed to extract project name from {metadata_path} - {e}")
        return None

def parse_metadata(metadata_path: str) -> dict:
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
        raise ValueError(f"Error: Failed to parse metadata in {metadata_path} - {e}")
    
    return metadata

def calculate_dimensions(metadata: dict, fov_width: float = 77.75, fov_height: float = 51.83) -> Tuple[float, float]:
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

def find_matching_files(metadata_dir: str, image_dir: str) -> List[Tuple[str, str]]:
    """Find matching pairs of image and metadata files."""
    supported_formats = {'.jpg', '.jpeg', '.tif', '.tiff', '.png'}
    
    metadata_files = {f for f in os.listdir(metadata_dir) if f.endswith('.txt')}
    image_files = {f for f in os.listdir(image_dir) 
                  if os.path.splitext(f)[1].lower() in supported_formats}
    
    metadata_lookup = {}
    for metadata_file in metadata_files:
        metadata_path = os.path.join(metadata_dir, metadata_file)
        project_name = extract_project_name(metadata_path)
        if project_name:
            metadata_lookup[project_name] = metadata_file
    
    matches = []
    for img in image_files:
        base_name = os.path.splitext(img)[0]  # Remove extension
        if base_name in metadata_lookup:
            matches.append((
                os.path.join(metadata_dir, metadata_lookup[base_name]),
                os.path.join(image_dir, img)
            ))
    
    return matches

def process_files(metadata_dir: str, image_dir: str, output_file: str):
    """Process all matching image and metadata files to calculate dimensions."""
    if not os.path.exists(metadata_dir) or not os.path.exists(image_dir):
        log("Error: Metadata or image directory does not exist")
        return
    
    existing_data = set()
    if os.path.exists(output_file):
        existing_df = pd.read_csv(output_file)
        existing_data = set(existing_df['drawer_id'])
    
    file_pairs = find_matching_files(metadata_dir, image_dir)
    if not file_pairs:
        log("No matching pairs found")
        return
    
    log(f"Found {len(file_pairs)} matching pairs")
    
    processed = 0
    skipped = 0
    results = []
    
    for i, (metadata_path, image_path) in enumerate(file_pairs, 1):
        try:
            drawer_id = os.path.splitext(os.path.basename(image_path))[0]
            
            if drawer_id in existing_data:
                log_progress("process_metadata", i, len(file_pairs), f"Skipped {drawer_id} (already exists)")
                skipped += 1
                continue
            
            metadata = parse_metadata(metadata_path)
            width_px, height_px = Image.open(image_path).size
            
            width_mm, height_mm = calculate_dimensions(metadata)
            width_ratio = width_px / width_mm
            height_ratio = height_px / height_mm
            pixel_to_mm_ratio = round((width_ratio + height_ratio) / 2, 2)
            
            results.append({
                'drawer_id': drawer_id,
                'image_height_mm': round(height_mm, 2),
                'image_width_mm': round(width_mm, 2),
                'image_height_px': height_px,
                'image_width_px': width_px,
                'px_mm_ratio': pixel_to_mm_ratio
            })
            
            log_progress("process_metadata", i, len(file_pairs), f"Processed {drawer_id}")
            processed += 1
            
        except Exception as e:
            log(f"Error: {os.path.basename(image_path)} - {e}")
            continue
    
    if results:
        new_df = pd.DataFrame(results)
        if os.path.exists(output_file):
            new_df.to_csv(output_file, mode='a', header=False, index=False)
        else:
            new_df.to_csv(output_file, index=False)
        
    log(f"Complete. Processed: {processed}, Skipped: {skipped}")
