import os
import json
import shutil
import time
from PIL import Image, ImageDraw
from concurrent.futures import ProcessPoolExecutor
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def process_mask(args):
    image_path, json_path, output_dir, base_name = args
    
    try:
        with Image.open(image_path).convert("RGB") as mask_image:
            if json_path and os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                pin_count = 0
                pin_polygons = []
                for pred in data.get('predictions', []):
                    if pred['class'] == 'pin':
                        points = [(point['x'], point['y']) for point in pred['points']]
                        pin_polygons.append(points)
                        pin_count += 1
                
                if pin_count > 1:
                    # Create separate masks for each pin
                    for i, points in enumerate(pin_polygons, start=1):
                        separate_mask = mask_image.copy()
                        draw = ImageDraw.Draw(separate_mask)
                        draw.polygon(points, fill="black")
                        separate_output_path = os.path.join(output_dir, f"{base_name}_fullmask_{i}.png")
                        separate_mask.save(separate_output_path)
                    return f"Multiple pins detected for {base_name}. Created {pin_count} masks."
                elif pin_count == 1:
                    # Single pin, create one mask
                    draw = ImageDraw.Draw(mask_image)
                    draw.polygon(pin_polygons[0], fill="black")
                    output_path = os.path.join(output_dir, f"{base_name}_fullmask.png")
                    mask_image.save(output_path)
                    return f"Added 1 pin to {base_name}."
                else:
                    # No pins, copy original image
                    output_path = os.path.join(output_dir, f"{base_name}_fullmask_unedited.png")
                    shutil.copy(image_path, output_path)
                    return f"No pins found in {base_name}."
            else:
                # No JSON file, copy original image
                output_path = os.path.join(output_dir, f"{base_name}_fullmask_unedited.png")
                shutil.copy(image_path, output_path)
                return f"No JSON for {base_name}."
    except Exception as e:
        return f"Error processing {image_path}: {str(e)}"

def create_pinmask(image_input_dir, coord_input_dir, output_dir):
    start_time = time.time()
    tasks = []
    
    for root, _, files in os.walk(image_input_dir):
        for file in files:
            if not file.endswith('.png'):
                continue
                
            full_id = file.replace('.png', '')
            image_path = os.path.join(root, file)
            rel_path = os.path.relpath(root, image_input_dir)
            
            json_path = os.path.join(coord_input_dir, rel_path, f"{full_id}_masked.json")
            out_subfolder = os.path.join(output_dir, rel_path)
            os.makedirs(out_subfolder, exist_ok=True)
            
            tasks.append((image_path, json_path, out_subfolder, full_id))
    
    with ProcessPoolExecutor() as executor:
        for result in executor.map(process_mask, tasks):
            logger.info(result)
    
    logger.info(f"\nProcessed {len(tasks)} masks in {time.time() - start_time:.1f}s")



