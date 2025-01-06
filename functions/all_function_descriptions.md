## ⚙️ Summary of Processing Steps

Below, we list and describe all steps used in the processing script.

### Model Configuration Notes

🟣 **Roboflow Model Steps**
- [Customize confidence and overlap](https://docs.roboflow.com/deploy/hosted-api/custom-models/object-detection) percentages (0-100) when applicable
- Confidence = only annotations the model is [X]% or more confident in will be recorded.
- Overlap = the model expects object bounding boxes to overlap by up to [X]%.
  - Only for object detection  

🟧 **Anthropic OCR Steps**
- Uses Claude API for text recognition
- Prompts can be edited as-needed, see:
  - `ocr_header.py`
  - `ocr_label.py`
  - `ocr_validation.py`

### 1. Resize Drawer Images

**Description**

Resizes full-size drawer images to create 1000px-wide versions for inference.

**Command**
```sh
python process_images.py resize_drawers
```

**Inputs**
- Original whole-drawer images
  - Location: drawers/fullsize/
  - Filetype: JPG
  - Format: [drawer_id].jpg

**Outputs**

- Resized drawer images
  - Location: drawers/resized/
  - Filetype: JPG
  - Format: [drawer_id]_1000.jpg

**Dependencies**
- No prior steps required (this is typically the first step)

### 2. Calculate Size Ratios from Metadata - FMNH Only
**Description**

Calculates pixel-to-millimeter conversion ratios for each drawer.

**Command**
```sh
python process_images.py process_metadata
```

**Inputs**
- Metadata text files from GIGAMacro capture system
  - Location: drawers/fullsize/capture_metadata/
  - Filetype: TXT
  - Format: [drawer_id].txt
- Original drawer images
  - Location: drawers/fullsize/
  - Filetype: JPG
  - Format: [drawer_id].jpg
    
**Outputs**
- CSV files with px-to-mm ratios for each [drawer_id].jpg
  - Location: drawers/fullsize/capture_metadata/sizeratios.csv
  - Filetype: CSV
  - Fields: drawer_id, image_height_mm, image_width_mm, image_height_px, image_width_px, px_mm_ratio
 
**Dependencies**
- TXT file manually added to drawers/fullsize/capture_metadata/

### 3. 🟣 Find Tray Coordinates

**Description**

Uses Roboflow object detection to locate unit trays.

**Command**
```sh
python process_images.py infer_drawers --drawer_confidence 50 --drawer_overlap 50
```

**Inputs**
- Resized drawer images
  - Location: drawers/resized/
  - Filetype: JPG
  - Format: [drawer_id]_1000.jpg

**Outputs**
- Tray coordinate predictions
  - Location: drawers/resized/coordinates
  - Filetype: JSON
  - Format: [drawer_id]_1000.json

**Dependencies**
- Resized Drawer Images (Step 1)

### 4. Crop Trays from Drawers

**Description**

Crops individual unit trays from full-size drawer images using scaled-up coordinates.

**Command**
```sh
python process_images.py crop_trays
```

**Inputs**
- Full-size drawer images
  - Location: drawers/fullsize/
  - Filetype: JPG
- Resized drawer images
  - Location: drawers/resized/
  - Filetype: _1000.jpg
- Tray coordinate predictions
  - Location: drawers/resized/coordinates
  - Filetype: JSON
  - Format: [drawer_id]_1000.json

**Outputs**
- Individual tray images
  - Location: drawers/trays/[drawer_id]/
  - Filetype: JPG
  - Format: [drawer_id][tray_##].jpg

**Dependencies**
- Resize Drawer Images (Step 1)
- Find Tray Coordinates (Step 3)

### 5. Resize Trays

**Description**

Creates 1000px-wide versions of cropped tray images for inference.

**Command**
```sh
python process_images.py resize_trays
```

**Inputs**
- Original tray images
  - Location: drawers/trays/[drawer_id]/
  - Filetype: JPG 

**Outputs**
- Resized tray images
  - Location: drawers/resized_trays/[drawer_id]/
  - Filetype: JPG 
  - Format: [drawer_id][tray_##]_1000.jpg

**Dependencies**
- Crop Trays from Drawers (Step 4)

### 6. 🟣 Find Tray Label Coordinates

**Description**

Uses Roboflow object detection to locate barcodes, QR codes, geocodes, and taxonomic text from tray header labels.

**Command**
```sh
python process_images.py infer_labels --label_confidence 50 --label_overlap 50
```

**Inputs**
- Resized tray images
  - Location: drawers/resized_trays/[drawer_id]/
  - Filetype: JPG 
  - Format: [drawer_id][tray_##]_1000.jpg

**Outputs**
- Tray label bounding box coordinates
  - Location: drawers/resized_trays/label_coordinates/##/
  - Filetype: JSON
  - Format: [drawer_id][tray_##]_1000_label.json
  - Classes: barcode, geocode, label, qr

**Dependencies**
- Resize Trays (Step 5)

### 7. Crop Tray Label Components

**Description**

Crops label components (barcodes, geocodes, text labels) from full-size tray images.

**Command**
```sh
# Full processing
python process_images.py crop_labels
```

**Inputs**
- Original tray images
  - Location: drawers/trays/[drawer_id]/
  - Filetype: JPG
  - [drawer_id][tray_##].jpg
- Resized tray images
  - Location: drawers/resized_trays/[drawer_id]/
  - Filetype: JPG 
  - Format: [drawer_id][tray_##]_1000.jpg
- Tray label bounding box coordinates
  - Location: drawers/resized_trays/label_coordinates/##/
  - Filetype: JSON
  - Format: [drawer_id][tray_##]_1000_label.json

**Outputs**
- Cropped label components
  - Location: drawers/labels/[drawer_id]/[##]/
  - Filetype: JPG
  - Formats:
    - [drawer_id][tray_##]_barcode.jpg
    - [drawer_id][tray_##]_label.jpg

**Dependencies**
- Crop Trays from Drawers (Step 4)
- Resize Trays (Step 5)
- Find Tray Label Coordinates (Step 6)

### 8. 🟣 Find Specimen Coordinates

**Description**

Uses Roboflow object detection to locate individual specimens.

**Command**
```sh
# Full processing
python process_images.py infer_trays --tray_confidence 50 --tray_overlap 50
```

**Inputs**
- Resized tray images
  - Location: drawers/trays_resized/[drawer_id]/
  - Filetype: JPG
  - Format: [drawer_id][tray_##]_1000.jpg

**Outputs**
- Specimen bounding box coordinates
  - Location: drawers/drawers/resized_trays/coordinates/[drawer_id]/[##]
  - Filetype: JSON
  - Format: [drawer_id][tray_##]_1000.json

**Dependencies**
- Resize Trays (Step 5)

### 9. Crop Specimens from Trays

**Description**

Crops specimens from tray images, in top-to-bottom, left-to-right order (001 = top-left corner)

**Command**
```sh
python process_images.py crop_specimens
```

**Inputs**
- Original tray images
  - Location: drawers/trays/[drawer_id]/
  - Filetype: JPG
  - Format: [drawer_id][tray_##].jpg
- Resized tray images
  - Location: drawers/trays_resized/[drawer_id]/
  - Filetype: JPG
  - Format: [drawer_id][tray_##]_1000.jpg
- Specimen bounding box coordinates
  - Location: drawers/resized_trays/coordinates/[drawer_id]/[##]
  - Filetype: JSON
  - Format: [drawer_id][tray_##]_1000.json

**Outputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id][tray_##][spec_###].jpg

**Dependencies**
- Crop Trays from Drawers (Step 4)
- Resize Trays (Step 5)
- 🟣 Find Specimen Coordinates (Step 8)

### 10. 🟣 Find Specimen Body Outlines

**Description**

Uses Roboflow instance segmentation to create precise outlines of specimen bodies, excluding legs, antennae, etc.

**Command**
```sh
python process_images.py infer_beetles --beetle_confidence 50
```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id][tray_##][spec_###].jpg

**Outputs**
- Coordinates of specimen's body outline
  - Location: drawers/masks/mask_coordinates/[drawer_id]/[##]/
  - Filetype: JSON
  - Format: [drawer_id][tray_##][spec_###].json

**Dependencies**
- Crop Specimens from Trays (Step 9)

### 11. Create Binary Mask PNGs

**Description**

Converts specimen outline coordinates into binary (black and white) masks.

**Command**
```sh
python process_images.py create_masks
```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id][tray_##][spec_###].jpg
- Coordinates of specimen's body outline
  - Location: drawers/masks/mask_coordinates/[drawer_id]/[##]/
  - Filetype: JSON
  - Format: [drawer_id][tray_##][spec_###].json

**Outputs**
- Binary masks (white = filled body-shaped polygon, black = background)
  - Location: drawers/masks/mask_png/[drawer_id]/[##]/
  - Filetype: PNG
  - Format: [drawer_id][tray_##][spec_###].png

**Dependencies**
- Crop Specimens from Trays (Step 9)
- Find Specimen Body Outlines (Step 10)

### 12. Fix Multi-Polygon Masks

**Description**

If there are multiple polygons in a binary mask, this function excludes the smaller (likely erroneous) polygon.

**Command**
```sh
python process_images.py fix_mask
```

**Inputs**
- Binary masks (white = filled body-shaped polygon, black = background)
  - Location: drawers/masks/mask_png/[drawer_id]/[##]/
  - Filetype: PNG
  - Format: [drawer_id][tray_##][spec_###].png

**Outputs**
- Fixed binary masks
  - Location: drawers/masks/mask_png/[drawer_id]/[##]/ _no change in mask location_
  - Filetype: PNG
  - Format: [drawer_id][tray_##][spec_###].png _no change in mask name_

**Dependencies**
- Create Binary Mask PNGs (Step 11)

### 13. Measure Specimens

**Description**

Calculates area and longest vertical length for each specimen.
  - FMNH / GIGAMacro ONLY: converts pixels to mm using sizeratios.csv

**Command**
```sh
python process_images.py process_and_measure_images
```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id][tray_##][spec_###].jpg
- Binary masks (white = filled body-shaped polygon, black = background)
  - Location: drawers/masks/mask_png/[drawer_id]/[##]/
  - Filetype: PNG
  - Format: [drawer_id][tray_##][spec_###].png
    
- FMNH ONLY: CSV file with px-to-mm ratios for each [drawer_id].jpg
  - Location: drawers/fullsize/capture_metadata/sizeratios.csv
  - Filetype: CSV
  - Fields Used: drawer_id, px_mm_ratio

**Outputs**
- Spreadsheet with length and area for each specimen and whether the image has a mask (mask_OK = Y) or not (mask_OK = N)
  - Location: drawers/measurements/
  - Filetype: CSV
  - Format: measurements.csv
  - Fields: full_id, drawer_id, tray_id, longest_px, area_px, mask_OK
    - FMNH-ONLY: spec_length_mm, spec_area_mm2, longest_px, missing_size, bad_size 
- Measurement visualizations
  - Location: drawers/measurements/visuals/[drawer_id]/[##]
  - Filetype: PNG
  - Format: [drawer_id][tray_##][spec_###]_measured.png

**Dependencies**
- Crop Specimens from Trays (Step 9)
- Create Binary Mask PNGs (Step 11)
- Fix Multi-Polygon Masks (Step 12)
- FMNH ONLY: Calculate Pixel:MM Ratios (Step 2)

### 14. Remove Background

**Description**

Uses binary masks to remove background pixels from specimen images.

**Command**
```sh
python process_images.py censor_background
```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id][tray_##][spec_###].jpg
- Binary masks (white = filled body-shaped polygon, black = background)
  - Location: drawers/masks/mask_png/[drawer_id]/[##]/
  - Filetype: PNG
  - Format: [drawer_id][tray_##][spec_###].png

**Outputs**
- Specimen images with whited-out backgrounds
  - Location: drawers/masks/no_background/[drawer_id]/[##]/
  - Filetype: PNG 
  - Format: [drawer_id][tray_##][spec_###]_masked.png

**Dependencies**
- Crop Specimens from Trays (Step 9)
- Create Binary Mask PNGs (Step 11)

### 15. 🟣 Find Pin Outlines 

**Description**

Uses Roboflow instance segmentation to detect mounting pins in censored (no-background) specimen images.
- Note: this step only runs on images that have been successfully masked, e.g., where mask_OK = Y

**Command**
```sh
python process_images.py infer_pins
```

**Inputs**
- Specimen images with whited-out backgrounds
  - Location: drawers/masked_specimens/[drawer_id]/[##]/
  - Filetype: PNG
  - Format: [drawer_id][tray_##][spec_###]_masked.png
- 'mask_OK' field from measurement data
  - Location: drawers/measurements/
  - Filetype: CSV
  - Format: measurements.csv

**Outputs**
- Coordinates of the pin outline
  - Location: drawers/masks/pin_coords/[drawer_id]/[##]/
  - Filetype: JSON
  - Format: [drawer_id][tray_##][spec_###]_masked.json

**Dependencies**
- Remove Background (Step 14)
- Measure Specimens (Step 13)

### 16. Create Complete Binary Masks

**Description**

Creates the final binary masks where specimen body = white, pin and background = black.
- To help filter out pin segmentation errors, the script creates multiple masks for a single specimen where 2 or more 'pins' are detected

**Command**
```sh
python process_images.py create_pinmask
```

**Inputs**
- Specimen images with whited-out backgrounds
  - Location: drawers/masked_specimens/[drawer_id]/[##]/
  - Filetype: PNG
  - Format: [drawer_id][tray_##][spec_###]_masked.png
- Coordinates of the pin outline
  - Location: drawers/masks/pin_coords/[drawer_id]/[##]/
  - Filetype: JSON
  - Format: [drawer_id][tray_##][spec_###]_masked.json

**Outputs**
- Full binary masks with pins
  - Location: drawers/masks/full_masks/[drawer_id]/[##]/
  - Filetype: PNG
  - Formats:
    - [drawer_id][tray_##][spec_###]_fullmask.png _if a single pin is detected_
    - [drawer_id][tray_##][spec_###]_fullmask_1.png, _fullmask_2.png, etc. _if multiple 'pins' are detected, likely an ERROR_
    - [drawer_id][tray_##][spec_###]_fullmask_unedited.png _if no pins are detected or no JSON is found_

**Dependencies**
- 🟣 Find Pin Outlines (Step 15)
- Remove Background (Step 14)

### 17. Create Full Transparencies

**Description**

Creates final specimen images with transparent backgrounds using completed masks.

**Command**
```sh
python process_images.py create_transparency
```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id][tray_##][spec_###].jpg
- Full binary masks with pins
  - Location: drawers/masks/full_masks/[drawer_id]/[##]/
  - Filetype: PNG
  - Formats:
    - [drawer_id][tray_##][spec_###]_fullmask.png IF 1 PIN IS DETECTED
    - [drawer_id][tray_##][spec_###]_fullmask_1.png, _fullmask_2.png, etc. IF MULTIPLE PINS DETECTED (likely error)
    - [drawer_id][tray_##][spec_###]_fullmask_unedited.png IF 0 PINS ARE DETECTED

**Outputs**
- Full-color specimen photos with the pin and background transparent
  - Location: drawers/transparencies/[drawer_id]/[##]/
  - Filetype: PNG
  - Format: [drawer_id][tray_##][spec_###]_finalmask.png

**Dependencies**
- Create Complete Binary Masks (Step 16)
- Crop Specimens from Trays (Step 9)

### 18. 🟧 Transcribe Visible Specimen Labels

**Description**

Rotates specimen images, then uses Claude to transcribe any visible text and estimate the specimen's collection location.
- Also logs time, cost, and errors

**Command**
```sh
python process_images.py transcribe_images
```

**Prompts**

```sh

## Verbatim text transcription from images

transcription_response = await self.api_call_with_retry(
  model="claude-3-5-sonnet-20241022",
  max_tokens=1000,
  system="You are a label transcription tool. You may encounter fragmented or handwritten text. Output text only, no descriptions or commentary.",
  messages=[{
    "role": "user",
    "content": [
      {
        "type": "text",
        "text": "Transcribe any visible text. Output 'no text found' if none visible. Transcribe text verbatim. No explanations, descriptions, or commentary."

```

```sh

## Location estimation from verbatim text

location_response = await self.api_call_with_retry(
  model="claude-3-5-sonnet-20241022",
  max_tokens=1000,
  system="You are a geographic data extractor, reconstructing locations from fragments of text. Output locations only, no explanations.",
  messages=[{
    "role": "user",
    "content": f"Extract geographic location from this text: {transcription}. Format: largest to smallest unit, comma-separated. Output 'no location found' if none present. No explanations or notes."

```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id][tray_##][spec_###].jpg

**Outputs**
- Label transcription data
  - Location: drawers/transcriptions/specimen_labels/
  - Filetype: CSV
  - Format: location_frags.csv
  - Fields: 'filename', 'transcription', 'location', 'transcription_tokens', 'location_tokens', 'processing_time', 'error'

**Dependencies**
- Crop Specimens from Trays (Step 9)

### 19. 🟧 Validate Locations

**Description**

Cross-checks and standardizes location data extracted from specimen labels using Claude, outputting a final CSV with a final guess and flags for poor estimates

**Command**
```sh
python process_images.py validate_transcription
```

**Prompt**
```sh

## Prompt for checking and standardizing location estimates

VALIDATION_PROMPT = """You are a geographic data validator specializing in museum specimen labels. Your task is to:
1. Examine the transcribed text and interpreted location for consistency
2. Make a final location determination considering:
   - The verbatim transcribed text
   - The proposed location interpretation
   - Your knowledge of geographic conventions in natural history collections
   - Historical place names and abbreviations
   - Locations derived from 'Field Museum' or 'FMNH' or 'Chicago Field Museum' are INVALID, as this is where the specimens are housed

Respond in this format:
{
'verbatim_text': 'exact text as transcribed',
'proposed_location': 'location as interpreted',
'validation_status': 'VALID/UNCERTAIN/INVALID/INSUFFICIENT',
'final_location': 'your final location determination, 'UNKNOWN' if unknown/missing/invalid',
'confidence_notes': 'brief explanation of your reasoning'
}

Consider:
- State/country abbreviations (e.g., IL = Illinois)
- Common collector shorthand (e.g., 'Co.' = County)
- Historical place names
- Level of certainty needed for scientific records"""

```

**Inputs**
- Label transcription data
  - Location: drawers/transcriptions/specimen_labels/
  - Filetype: CSV
  - Format: location_frags.csv
  - Fields: 'filename', 'transcription', 'location', 'transcription_tokens', 'location_tokens', 'processing_time', 'error'

**Outputs**
- Cross-checked location data
  - Location: drawers/transcriptions/specimen_labels/
  - Filetype: CSV
  - Format: location_checked.csv
  - Fields: 'filename', 'verbatim_text', 'proposed_location', 'validation_status', 'final_location', 'confidence_notes', 'processing_time', 'error'

**Dependencies**
- 🟧 Transcribe Visible Specimen Labels (Step 18)


### 20. 🟧 Process Unit Tray Headers

**Description**

Uses Claude to transcribe barcodes and/or taxonomic names from header labels
- Main script toggles can be set up for just barcodes, just taxonomic names, or both
- We highly recommend tailoring the prompts to match your header label structure!

**Commands**
```sh
# Barcodes
python test_process_images.py process_barcodes

# Taxonomy
python process_images.py transcribe_taxonomy
```

**Prompts**
```sh

## Barcode transcription

BARCODE_CONFIG = TranscriptionConfig(
    file_suffix='_barcode.jpg',
    system_prompt="You are a barcode reading tool. You should output only the number (or letter-number string) found in the image. If no valid barcode is found, output 'none'.",
    user_prompt="Read the barcode number. Output only the number, no explanations.",
    csv_fields=['tray_id', 'unit_barcode'],
    validation_func=lambda x: {'unit_barcode': 'no_barcode' if x.lower() == 'none' else x}
)

```

```sh

## Taxonomy transcription

LABEL_CONFIG = TranscriptionConfig(
    file_suffix='_label.jpg',
    system_prompt="""You are a taxonomic label transcription tool specializing in natural history specimens. Your task is to:
1. Provide a complete transcription of the entire label
2. Extract the taxonomic name, including any genus, subgenus, species, and subspecies information
3. Extract the taxonomic authority (author and year)

For missing elements, output 'none'. Format your response as a structured dictionary with these three keys:
{
'full_transcription': 'complete text as shown',
'taxonomy': 'only taxonomic name (Genus (Subgenus) species subspecies)', 
'authority': 'author, year'
}""",
    user_prompt="Transcribe this taxonomic label, preserving the exact text and extracting the taxonomic name and authority. Output only the dictionary, no explanations.",
    csv_fields=['tray_id', 'full_transcription', 'taxonomy', 'authority']
)

```

**Inputs**
- Cropped label components
  - Location: drawers/labels/[drawer_id]/[##]/
  - Filetype: JPG
  - Formats:
    - [drawer_id][tray_##]_barcode.jpg
    - [drawer_id][tray_##]_label.jpg

**Outputs**
- Barcode data
  - Location: drawers/transcriptions/tray_labels
  - Filetype: CSV
  - Format: unit_barcodes.csv
  - Fields: tray_id, unit_barcode
- Taxonomic ID data
  - Location: drawers/transcriptions/tray_labels
  - Filetype: CSV
  - Format: taxonomy.csv
  - Fields: tray_id, full_transcription, taxonomy, authority

**Dependencies**
- Crop Tray Label Components (Step 7)

