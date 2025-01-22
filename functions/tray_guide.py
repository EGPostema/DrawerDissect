import os
import json
import time
from PIL import Image, ImageDraw, ImageFont
from multiprocessing import Pool, cpu_count

# Allow processing of large images
Image.MAX_IMAGE_PIXELS = None

def create_guide(args):
    trays_dir, resized_trays_dir, guides_dir, root, resized_filename = args
    
    # Parse filename components
    base_name = resized_filename.replace('_1000.jpg', '')
    drawer_name = '_'.join(base_name.split('_')[:-2])
    tray_num = base_name.split('_')[-1]
    
    # Setup paths
    original_path = os.path.join(trays_dir, drawer_name, f"{base_name}.jpg")
    json_path = os.path.join(resized_trays_dir, 'coordinates', f"{base_name}_1000.json")
    
    if not os.path.exists(json_path) or not os.path.exists(original_path):
        return f"Skipped {base_name}: Missing required files"

    # Create guides directory if it doesn't exist
    os.makedirs(guides_dir, exist_ok=True)
    
    try:
        # Load and parse JSON
        with open(json_path, 'r') as f:
            data = json.load(f)
            annotations = data.get('predictions', [])
            resized_dimensions = data.get('image', {})
            if not all(key in resized_dimensions for key in ['width', 'height']):
                return f"Skipped {base_name}: Missing image dimensions in JSON"
        
        # Sort annotations in the same way as the specimen script
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
        
        # Open and process the image
        with Image.open(original_path) as img:
            # Create a copy to draw on
            guide_img = img.copy()
            draw = ImageDraw.Draw(guide_img)
            
            # Calculate scale factors
            scale_x = guide_img.width / float(resized_dimensions['width'])
            scale_y = guide_img.height / float(resized_dimensions['height'])
            
            # Calculate font size based on image dimensions
            font_size = int(min(guide_img.width, guide_img.height) * 0.02)  # 2% of smaller dimension
            try:
                # Try to use Arial bold, fallback to default
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # Draw boxes and numbers
            line_width = max(1, int(min(guide_img.width, guide_img.height) * 0.002))  # 0.2% of smaller dimension
            
            for idx, ann in enumerate(sorted_annotations, 1):
                x, y = ann['x'], ann['y']
                width, height = ann['width'], ann['height']
                
                # Calculate box coordinates
                xmin = int((x - width/2) * scale_x)
                ymin = int((y - height/2) * scale_y)
                xmax = int((x + width/2) * scale_x)
                ymax = int((y + height/2) * scale_y)
                
                # Draw red rectangle
                draw.rectangle(
                    [(xmin, ymin), (xmax, ymax)],
                    outline='red',
                    width=line_width
                )
                
                # Add specimen number
                number = f"{idx:03}"
                # Get text size for positioning
                try:
                    text_bbox = draw.textbbox((0, 0), number, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                except:
                    text_width = font_size * len(number) * 0.6
                    text_height = font_size
                
                # Position text at bottom left of box with padding
                padding = line_width * 2
                text_x = xmin + padding
                text_y = ymax - text_height - padding
                
                # Draw white background for text
                draw.rectangle(
                    [(text_x - padding, text_y - padding),
                     (text_x + text_width + padding, text_y + text_height + padding)],
                    fill='white'
                )
                
                # Draw text
                draw.text(
                    (text_x, text_y),
                    number,
                    fill='red',
                    font=font
                )
            
            # Save the guide image
            output_path = os.path.join(guides_dir, f"{base_name}_guide.jpg")
            guide_img.save(output_path, quality=95)
            
            return f"Created guide for {base_name}"
            
    except Exception as e:
        return f"Failed {base_name}: {str(e)}"

def create_tray_guides(trays_dir, resized_trays_dir, guides_dir):
    """
    Create visual guides for all trays showing specimen numbers.
    
    Args:
        trays_dir (str): Directory containing original tray images
        resized_trays_dir (str): Directory containing resized images and coordinates
        guides_dir (str): Directory where guide images will be saved
    """
    start_time = time.time()
    
    tasks = []
    for root, _, files in os.walk(resized_trays_dir):
        tasks.extend([
            (trays_dir, resized_trays_dir, guides_dir, root, f)
            for f in files if f.endswith('_1000.jpg')
        ])
    
    with Pool(cpu_count()) as pool:
        results = pool.map(create_guide, tasks)
    
    for result in results:
        print(result)
    
    elapsed_time = time.time() - start_time
    print(f"\nProcessing complete. Total time: {elapsed_time:.2f} seconds")
