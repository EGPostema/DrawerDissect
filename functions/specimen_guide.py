import os
import json
from PIL import Image, ImageDraw, ImageFont
from multiprocessing import Pool, cpu_count

Image.MAX_IMAGE_PIXELS = None

def create_guide(args):
    resized_trays_dir, guides_dir, root, resized_filename = args
    base_name = resized_filename.replace('_1000.jpg', '')
    rel_path = os.path.relpath(root, resized_trays_dir)
    if rel_path == '.':
        rel_path = ''
    
    # Work directly with resized image
    resized_image_path = os.path.join(root, resized_filename)
    if not os.path.exists(resized_image_path):
        return f"Skipped {base_name}: Resized image not found"

    json_path = os.path.join(resized_trays_dir, 'coordinates', f"{base_name}_1000.json")
    
    if not os.path.exists(json_path):
        return f"Skipped {base_name}: Missing JSON file"

    guide_output_dir = os.path.join(guides_dir, rel_path)
    os.makedirs(guide_output_dir, exist_ok=True)
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            annotations = data.get('predictions', [])
            resized_dimensions = data.get('image', {})
            if not all(key in resized_dimensions for key in ['width', 'height']):
                return f"Skipped {base_name}: Missing image dimensions in JSON"
        
        row_threshold = 50
        sorted_annotations = []
        current_row = []
        last_y = None
        
        for ann in sorted(annotations, key=lambda a: (a['y'], a['x'])):
            if last_y is None or abs(ann['y'] - last_y) > row_threshold:
                if current_row:
                    sorted_annotations.extend(sorted(current_row, key=lambda a: a['x']))
                current_row = [ann]
                last_y = ann['y']
            else:
                current_row.append(ann)
        if current_row:
            sorted_annotations.extend(sorted(current_row, key=lambda a: a['x']))
        
        with Image.open(resized_image_path) as img:
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGB')
            
            guide_img = img.copy()
            draw = ImageDraw.Draw(guide_img)
            
            font_size = int(min(guide_img.width, guide_img.height) * 0.02)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            line_width = max(1, int(min(guide_img.width, guide_img.height) * 0.002))
            
            for idx, ann in enumerate(sorted_annotations, 1):
                x, y = ann['x'], ann['y']
                width, height = ann['width'], ann['height']
                
                xmin = int(x - width/2)
                ymin = int(y - height/2)
                xmax = int(x + width/2)
                ymax = int(y + height/2)
                
                draw.rectangle(
                    [(xmin, ymin), (xmax, ymax)],
                    outline='red',
                    width=line_width
                )
                
                number = f"{idx:03}"
                try:
                    text_bbox = draw.textbbox((0, 0), number, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                except:
                    text_width = font_size * len(number) * 0.6
                    text_height = font_size
                
                padding = line_width * 2
                text_x = xmin + padding
                text_y = ymax - text_height - padding
                
                draw.rectangle(
                    [(text_x - padding, text_y - padding),
                     (text_x + text_width + padding, text_y + text_height + padding)],
                    fill='white'
                )
                
                draw.text(
                    (text_x, text_y),
                    number,
                    fill='red',
                    font=font
                )
            
            output_path = os.path.join(guide_output_dir, f"{base_name}_guide.jpg")
            guide_img.save(output_path, quality=95)
            
            return f"Created guide for {base_name}"
            
    except Exception as e:
        return f"Failed {base_name}: {str(e)}"

def create_specimen_guides(resized_trays_dir, guides_dir):
    """
    Create visual guides for all trays showing specimen numbers.
    Works directly with resized images.
    
    Args:
        resized_trays_dir (str): Directory containing resized images and coordinates
        guides_dir (str): Directory where guide images will be saved
    """
    
    tasks = []
    for root, _, files in os.walk(resized_trays_dir):
        tasks.extend([
            (resized_trays_dir, guides_dir, root, f)
            for f in files if f.endswith('_1000.jpg')
        ])
    
    with Pool(cpu_count()) as pool:
        results = pool.map(create_guide, tasks)
    
    for result in results:
        print(result)