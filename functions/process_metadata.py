import os
import re
import pandas as pd
from PIL import Image, ImageFile
from multiprocessing import Pool, cpu_count

# Allow opening very large images
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def parse_metadata(metadata_path):
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
    horizontal_overlap = metadata['project_image_overlap']
    vertical_overlap = metadata['project_image_overlap_vertical']
    columns = metadata['project_columns']
    rows = metadata['project_rows']
    
    effective_fov_width = fov_width * (1 - horizontal_overlap)
    effective_fov_height = fov_height * (1 - vertical_overlap)
    
    total_width_mm = (columns - 1) * effective_fov_width + fov_width
    total_height_mm = (rows - 1) * effective_fov_height + fov_height
    
    return total_width_mm, total_height_mm

def process_file(args):
    metadata_dir, image_dir, filename = args
    results = []
    
    drawer_name = filename.replace('.txt', '')
    image_filename = f"{drawer_name}.jpg"
    image_path = os.path.join(image_dir, image_filename)
    
    if not os.path.exists(image_path):
        print(f"No matching image file found for {filename}")
        return results
    
    metadata_path = os.path.join(metadata_dir, filename)
    metadata = parse_metadata(metadata_path)
    
    with Image.open(image_path) as img:
        width_px, height_px = img.size
    
    width_mm, height_mm = calculate_dimensions(metadata)
    width_ratio = width_px / width_mm
    height_ratio = height_px / height_mm
    pixel_to_mm_ratio = round((width_ratio + height_ratio) / 2, 2)
    
    results.append({
        'drawer_id': drawer_name,
        'image_height_mm': round(height_mm, 2),
        'image_width_mm': round(width_mm, 2),
        'image_height_px': height_px,
        'image_width_px': width_px,
        'px_mm_ratio': pixel_to_mm_ratio
    })
    
    return results

def process_files(metadata_dir, image_dir, output_file):
    if not os.path.exists(metadata_dir) or not os.path.exists(image_dir):
        raise FileNotFoundError("Metadata or image directory does not exist. Please check the paths.")
    
    files = [f for f in os.listdir(metadata_dir) if f.endswith(".txt")]
    args = [(metadata_dir, image_dir, f) for f in files]

    with Pool(cpu_count()) as pool:
        results = pool.map(process_file, args)
    
    results = [item for sublist in results for item in sublist]
    
    df = pd.DataFrame(results)
    if df.empty:
        print("No valid results found. Exiting...")
        return
    
    df.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")

