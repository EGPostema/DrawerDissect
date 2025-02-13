import os
import json
import numpy as np
from PIL import Image, ImageDraw
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_mask(args):
    json_path, png_path = args
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        image_info = data.get('image', {})
        img_width = int(image_info.get('width', 0))
        img_height = int(image_info.get('height', 0))
        
        if not (img_width and img_height):
            return f"Skipped {json_path}: Invalid dimensions"
            
        binary_mask = Image.new('L', (img_width, img_height))
        draw = ImageDraw.Draw(binary_mask)
        
        for prediction in data.get('predictions', []):
            points = prediction.get('points', [])
            if not points:
                continue
                
            xy = [(int(point['x']), int(point['y'])) for point in points]
            draw.polygon(xy, outline=0, fill=255)
        
        binary_mask.save(png_path, optimize=True)
        return f"Processed {os.path.basename(json_path)}"
        
    except Exception as e:
        return f"Error with {json_path}: {str(e)}"

def create_masks(jsondir, pngdir):
    os.makedirs(pngdir, exist_ok=True)
    
    tasks = []
    for root, _, files in os.walk(jsondir):
        json_files = [f for f in files if f.endswith('.json')]
        if not json_files:
            continue
            
        rel_dir = os.path.relpath(root, jsondir)
        
        for file in json_files:
            json_path = os.path.join(root, file)
            png_path = os.path.join(pngdir, rel_dir, file.replace('.json', '.png'))
            
            if os.path.exists(png_path):
                continue
                
            os.makedirs(os.path.dirname(png_path), exist_ok=True)
            tasks.append((json_path, png_path))

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda x: process_mask(x), tasks))
        
    for result in results:
        logger.info(result)



