import os
import json
from PIL import Image, ImageFile
from concurrent.futures import ThreadPoolExecutor
import logging

Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_label(args):
    fullsize_dir, resized_dir, coordinates_dir, output_dir, root, resized_filename = args
    
    base_name_1000 = resized_filename.replace('.jpg', '')
    base_name = base_name_1000.replace('_1000', '')
    json_filename = f"{base_name_1000}_label.json"
    
    drawer_name = '_'.join(base_name.split('_')[:-2])
    tray_num = base_name.split('_')[-1]
    
    # Find original file with any supported extension
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    original_path = None
    original_ext = None
    
    for ext in supported_formats:
        test_path = os.path.join(fullsize_dir, drawer_name, f"{base_name}{ext}")
        if os.path.exists(test_path):
            original_path = test_path
            original_ext = ext
            break
            
    json_path = os.path.join(coordinates_dir, json_filename)
    output_folder = os.path.join(output_dir, drawer_name, tray_num)
    
    if not original_path:
        return f"Skipped {base_name}: Missing original file"
    if not os.path.exists(json_path):
        return f"Skipped {base_name}: Missing JSON file"

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            if not data.get('predictions'):
                return f"Skipped {base_name}: No predictions found"

        os.makedirs(output_folder, exist_ok=True)
        
        with Image.open(original_path) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGB')
                
            scale_x = img.width / float(data['image']['width'])
            scale_y = img.height / float(data['image']['height'])
            
            processed = set()
            for pred in data['predictions']:
                class_name = pred['class']
                if class_name not in ['barcode', 'geocode', 'label', 'qr']:
                    continue
                
                output_path = os.path.join(output_folder, f"{base_name}_{class_name}.jpg")
                if os.path.exists(output_path):
                    processed.add(class_name)
                    continue
                    
                x, y = pred['x'], pred['y']
                width, height = pred['width'], pred['height']
                
                xmin = max(int((x - width/2) * scale_x), 0)
                ymin = max(int((y - height/2) * scale_y), 0)
                xmax = min(int((x + width/2) * scale_x), img.width)
                ymax = min(int((y + height/2) * scale_y), img.height)
                
                cropped = img.crop((xmin, ymin, xmax, ymax))
                cropped.save(output_path)
                processed.add(class_name)
            
            return f"Processed {base_name}: Found {len(processed)} classes"
            
    except Exception as e:
        return f"Failed {base_name}: {str(e)}"

def crop_labels(fullsize_dir, resized_dir, coordinates_dir, output_dir):
    logging.getLogger().setLevel(logging.DEBUG)
    tasks = []
    for root, _, files in os.walk(resized_dir):
        for f in files:
            if f.endswith('_1000.jpg'):
                tasks.append((fullsize_dir, resized_dir, coordinates_dir, output_dir, root, f))

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda x: process_label(x), tasks))
    
    for result in results:
        logger.info(result)