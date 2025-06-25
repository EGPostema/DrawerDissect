import os
import json
from PIL import Image, ImageDraw, ImageFont
from multiprocessing import Pool, cpu_count
from logging_utils import log, log_found, log_progress

Image.MAX_IMAGE_PIXELS = None

def create_guide(args):
    """
    Create a visual guide for a single tray showing specimen numbers.
    """
    resized_trays_dir, guides_dir, root, resized_filename, current, total = args
    base_name = resized_filename.replace('_1000.jpg', '')
    
    # Calculate relative path to preserve directory structure
    rel_path = os.path.relpath(root, resized_trays_dir)
    if rel_path == '.':
        rel_path = ''
    
    # Work directly with resized image
    resized_image_path = os.path.join(root, resized_filename)
    if not os.path.exists(resized_image_path):
        log_progress("create_traymaps", current, total, f"Skipped {base_name} (image not found)")
        return False

    # Search recursively for the JSON file in the coordinates directory
    json_files = []
    for root_dir, _, files in os.walk(os.path.join(resized_trays_dir, 'coordinates')):
        for file in files:
            if file == f"{base_name}_1000.json":
                json_path = os.path.join(root_dir, file)
                json_files.append(json_path)
    
    # Use the first matching JSON if found
    json_path = json_files[0] if json_files else None
    
    if not json_path:
        log_progress("create_traymaps", current, total, f"Skipped {base_name} (JSON not found)")
        return False

    # Create output directory that mirrors input structure
    guide_output_dir = os.path.join(guides_dir, rel_path)
    os.makedirs(guide_output_dir, exist_ok=True)
    
    output_path = os.path.join(guide_output_dir, f"{base_name}_guide.jpg")
    if os.path.exists(output_path):
        log_progress("create_traymaps", current, total, f"Skipped {base_name} (already exists)")
        return False
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            annotations = data.get('predictions', [])
            resized_dimensions = data.get('image', {})
            if not all(key in resized_dimensions for key in ['width', 'height']):
                log(f"Skipped {base_name}: Missing image dimensions in JSON")
                return False
        
        # Organize specimens by row for consistent numbering
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
            
            # Set up font - try to use system font, fallback to default
            font_size = int(min(guide_img.width, guide_img.height) * 0.02)
            try:
                # Try a few common font options
                common_fonts = ["arial.ttf", "Arial.ttf", "Helvetica.ttf", "DejaVuSans.ttf"]
                font = None
                for font_name in common_fonts:
                    try:
                        font = ImageFont.truetype(font_name, font_size)
                        break
                    except:
                        continue
                        
                # Fall back to default if none of the above worked
                if font is None:
                    font = ImageFont.load_default()
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
                
                # Draw rectangle around specimen
                draw.rectangle(
                    [(xmin, ymin), (xmax, ymax)],
                    outline='red',
                    width=line_width
                )
                
                # Add specimen number
                number = f"{idx:03}"
                try:
                    # PIL has different ways to get text size depending on version
                    if hasattr(draw, 'textbbox'):
                        text_bbox = draw.textbbox((0, 0), number, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                    else:
                        text_width, text_height = draw.textsize(number, font=font)
                except:
                    # Fallback approximation
                    text_width = font_size * len(number) * 0.6
                    text_height = font_size
                
                padding = line_width * 2
                text_x = xmin + padding
                text_y = ymax - text_height - padding
                
                # Add white background behind number for readability
                draw.rectangle(
                    [(text_x - padding, text_y - padding),
                     (text_x + text_width + padding, text_y + text_height + padding)],
                    fill='white'
                )
                
                # Draw the number
                draw.text(
                    (text_x, text_y),
                    number,
                    fill='red',
                    font=font
                )
            
            # Save the guide image
            guide_img.save(output_path, quality=95)
            
            log_progress("create_traymaps", current, total, f"Processed {base_name} with {len(sorted_annotations)} specimens")
            return True
            
    except Exception as e:
        log(f"Error processing {base_name}: {str(e)}")
        return False

def create_specimen_guides(resized_trays_dir, guides_dir):
    """
    Create visual guides for all trays showing specimen numbers.
    Works directly with resized images.
    
    Args:
        resized_trays_dir (str): Directory containing resized images and coordinates
        guides_dir (str): Directory where guide images will be saved
    """
    # Ensure output directory exists
    os.makedirs(guides_dir, exist_ok=True)
    
    # Find all resized tray images
    tasks = []
    for root, _, files in os.walk(resized_trays_dir):
        for f in files:
            if f.endswith('_1000.jpg'):
                tasks.append((resized_trays_dir, guides_dir, root, f))
    
    if not tasks:
        log("No resized tray images found to process")
        return
        
    log_found("trays", len(tasks))
    
    # Add progress tracking indices
    tasks = [(t[0], t[1], t[2], t[3], i+1, len(tasks)) for i, t in enumerate(tasks)]
    
    # Process in parallel
    num_workers = min(cpu_count(), len(tasks))
    with Pool(num_workers) as pool:
        results = pool.map(create_guide, tasks)
    
    # Count results
    processed = sum(1 for r in results if r)
    skipped = len(tasks) - processed
