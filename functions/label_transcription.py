import os
import re
import pandas as pd
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

# Specify the base directory containing the resized_trays folder
base_directory = os.path.join(os.path.dirname(__file__), '../drawers/resized_trays')

# List to hold extracted data
data = []

# Function to extract label information
def extract_label_info(image_path):
    img = Image.open(image_path)
    cropped_img = img.crop((0, 0, img.width, 200))
    full_trans = pytesseract.image_to_string(cropped_img)
    lines = full_trans.split('\n')
    full_taxon = lines[0].strip()
    split_taxon = full_taxon.split()
    genus_species = ' '.join(split_taxon[:2])
    
    geo_code = ''
    year = ''
    
    for part in split_taxon:
        if part.isupper() and len(part) == 3:
            geo_code = part
        elif re.match(r'\d{4}', part):
            year = part
    
    for line in lines:
        if ',' in line:
            coll_year = line.split(',')
            year = coll_year[1].strip().replace(')', '')
        elif '(' in line and ')' in line:
            coll_year = line.split('(')
            year = coll_year[1].strip().replace(')', '')
    
    year_match = re.search(r'\d{4}', full_trans)
    if year_match:
        year = year_match.group(0)
    else:
        year = ''
    
    return {
        'image_file': os.path.basename(image_path),
        'extension': os.path.basename(image_path).replace('_1000.jpg', ''),
        'full_trans': full_trans,
        'full_taxon': genus_species,
        'year': year,
        'geo_code': geo_code
    }

# Function to preprocess image
def preprocess_image(image):
    grayscale = image.convert('L')
    enhancer = ImageEnhance.Contrast(grayscale)
    enhanced_image = enhancer.enhance(2)
    sharpened_image = enhanced_image.filter(ImageFilter.SHARPEN)
    binary_image = sharpened_image.point(lambda x: 0 if x < 128 else 255, '1')
    return binary_image

# Function to extract ID number from the top left region
def extract_id(image_path):
    img = Image.open(image_path)
    id_crop_img = img.crop((0, 0, 250, 250))
    preprocessed_img = preprocess_image(id_crop_img)
    id_code = pytesseract.image_to_string(preprocessed_img, config='--psm 6 -c tessedit_char_whitelist=0123456789').strip()
    
    match = re.search(r'\d{5}', id_code)
    if match:
        return match.group(0)
    else:
        return ''

def transcribe_labels_and_ids(resized_trays_dir):
    data = []
    for root, dirs, files in os.walk(resized_trays_dir):
        for file in files:
            if file.endswith('.jpg') and 'checkpoint' not in file:
                image_path = os.path.join(root, file)
                label_info = extract_label_info(image_path)
                label_info['id'] = extract_id(image_path)
                data.append(label_info)

    df = pd.DataFrame(data)
    label_data_directory = os.path.join(resized_trays_dir, 'label_data')
    os.makedirs(label_data_directory, exist_ok=True)
    csv_path = os.path.join(label_data_directory, 'labels.csv')
    df.to_csv(csv_path, index=False)
    print(f"Label data saved to {csv_path}")

if __name__ == '__main__':
    transcribe_labels_and_ids(drawers/resized_trays)
