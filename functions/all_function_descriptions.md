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
# Test environment
python test_process_images.py resize_drawers
# Full processing
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
# Test environment
python test_process_images.py process_metadata
# Full processing
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
# Test environment
python test_process_images.py infer_drawers --drawer_confidence 50 --drawer_overlap 50
# Full processing
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
# Test environment
python test_process_images.py crop_trays
# Full processing
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
  - Format: [drawer_id]_[tray_##].jpg

**Dependencies**
- Resize Drawer Images (Step 1)
- Find Tray Coordinates (Step 3)

### 5. Resize Trays

**Description**

Creates 1000px-wide versions of cropped tray images for inference.

**Command**
```sh
# Test environment
python test_process_images.py resize_trays
# Full processing
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
  - Format: [drawer_id]_[tray_##]_1000.jpg

**Dependencies**
- Crop Trays from Drawers (Step 4)

### 6. 🟣 Find Tray Label Coordinates

**Description**

Uses Roboflow object detection to locate barcodes, QR codes, geocodes, and taxonomic text from tray header labels.

**Command**
```sh
# Test environment
python test_process_images.py infer_labels --label_confidence 50 --label_overlap 50
# Full processing
python process_images.py infer_labels --label_confidence 50 --label_overlap 50
```

**Inputs**
- Resized tray images
  - Location: drawers/resized_trays/[drawer_id]/
  - Filetype: JPG 
  - Format: [drawer_id]_[tray_##]_1000.jpg

**Outputs**
- Tray label bounding box coordinates
  - Location: drawers/resized_trays/label_coordinates/##/
  - Filetype: JSON
  - Format: [drawer_id]_[tray_##]_1000_label.json
  - Classes: barcode, geocode, label, qr

**Dependencies**
- Resize Trays (Step 5)

### 7. Crop Tray Label Components

**Description**

Crops label components (barcodes, geocodes, text labels) from full-size tray images.

**Command**
```sh
# Test environment
python test_process_images.py crop_labels
# Full processing
python process_images.py crop_labels
```

**Inputs**
- Original tray images
  - Location: drawers/trays/[drawer_id]/
  - Filetype: JPG
  - [drawer_id]_[tray_##].jpg
- Resized tray images
  - Location: drawers/resized_trays/[drawer_id]/
  - Filetype: JPG 
  - Format: [drawer_id]_[tray_##]_1000.jpg
- Tray label bounding box coordinates
  - Location: drawers/resized_trays/label_coordinates/##/
  - Filetype: JSON
  - Format: [drawer_id]_[tray_##]_1000_label.json

**Outputs**
- Cropped label components
  - Location: drawers/labels/[drawer_id]/[##]/
  - Filetype: JPG
  - Formats:
    - [drawer_id]_[tray_##]_barcode.jpg
    - [drawer_id]_[tray_##]_label.jpg

**Dependencies**
- Crop Trays from Drawers (Step 4)
- Resize Trays (Step 5)
- Find Tray Label Coordinates (Step 6)

### 8. 🟣 Find Specimen Coordinates

**Description**

Uses Roboflow object detection to locate individual specimens.

**Command**
```sh
# Test environment
python test_process_images.py infer_trays --tray_confidence 50 --tray_overlap 50
# Full processing
python process_images.py infer_trays --tray_confidence 50 --tray_overlap 50
```

**Inputs**
- Resized tray images
  - Location: drawers/trays_resized/[drawer_id]/
  - Filetype: JPG
  - Format: [drawer_id]_[tray_##]_1000.jpg

**Outputs**
- Specimen bounding box coordinates
  - Location: drawers/drawers/resized_trays/coordinates/[drawer_id]/[##]
  - Filetype: JSON
  - Format: [drawer_id]_[tray_##]_1000.json

**Dependencies**
- Resize Trays (Step 5)

### 9. Crop Specimens from Trays

**Description**

Crops specimens from tray images, in top-to-bottom, left-to-right order (001 = top-left corner)

**Command**
```sh
# Test environment
python test_process_images.py crop_specimens
# Full processing
python process_images.py crop_specimens
```

**Inputs**
- Original tray images
  - Location: drawers/trays/[drawer_id]/
  - Filetype: JPG
  - Format: [drawer_id]_[tray_##].jpg
- Resized tray images
  - Location: drawers/trays_resized/[drawer_id]/
  - Filetype: JPG
  - Format: [drawer_id]_[tray_##]_1000.jpg
- Specimen bounding box coordinates
  - Location: drawers/resized_trays/coordinates/[drawer_id]/[##]
  - Filetype: JSON
  - Format: [drawer_id]_[tray_##]_1000.json

**Outputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id]_[tray_##]_[spec_###].jpg

**Dependencies**
- Crop Trays from Drawers (Step 4)
- Resize Trays (Step 5)
- 🟣 Find Specimen Coordinates (Step 8)

### 10. 🟣 Find Specimen Body Outlines

**Description**

Uses Roboflow instance segmentation to create precise outlines of specimen bodies.

**Command**
```sh
# Test environment
python test_process_images.py infer_beetles --beetle_confidence 50
# Full processing
python process_images.py infer_beetles --beetle_confidence 50
```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id]_[tray_##]_[spec_###].jpg

**Outputs**
- Coordinates of specimen's body outline
  - Location: drawers/masks/mask_coordinates/[drawer_id]/[##]/
  - Filetype: JSON
  - Format: [drawer_id]_[tray_##]_[spec_###].json

**Dependencies**
- Crop Specimens from Trays (Step 9)

### 11. Create Binary Mask PNGs

**Description**

Converts specimen outline coordinates into binary (black and white) masks.

**Command**
```sh
# Test environment
python test_process_images.py create_masks
# Full processing
python process_images.py create_masks
```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id]_[tray_##]_[spec_###].jpg
- Coordinates of specimen's body outline
  - Location: drawers/masks/mask_coordinates/[drawer_id]/[##]/
  - Filetype: JSON
  - Format: [drawer_id]_[tray_##]_[spec_###].json

**Outputs**
- Binary masks (white = filled body-shaped polygon, black = background)
  - Location: drawers/masks/mask_png/[drawer_id]/[##]/
  - Filetype: PNG
  - Format: [drawer_id]_[tray_##]_[spec_###].png

**Dependencies**
- Crop Specimens from Trays (Step 9)
- Find Specimen Body Outlines (Step 10)

### 12. Fix Multi-Polygon Masks

**Description**

If there are multiple polygons in a binary mask, this function excludes the smaller (likely erroneous) polygon.

**Command**
```sh
# Test environment
python test_process_images.py fix_mask
# Full processing
python process_images.py fix_mask
```

**Inputs**
- Binary masks (white = filled body-shaped polygon, black = background)
  - Location: drawers/masks/mask_png/[drawer_id]/[##]/
  - Filetype: PNG
  - Format: [drawer_id]_[tray_##]_[spec_###].png

**Outputs**
- Fixed binary masks
  - Location: drawers/masks/mask_png/[drawer_id]/[##]/ _no change_
  - Filetype: PNG
  - Format: [drawer_id]_[tray_##]_[spec_###].png _no change_

**Dependencies**
- Create Binary Mask PNGs (Step 11)

### 13. Measure Specimens

**Description**

Calculates area and longest vertical length for each specimen.
  - FMNH / GIGAMacro ONLY: converts pixels to mm using sizeratios.csv

**Command**
```sh
# Test environment
python test_process_images.py process_and_measure_images
# Full processing
python process_images.py process_and_measure_images
```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id]_[tray_##]_[spec_###].jpg
- Binary masks (white = filled body-shaped polygon, black = background)
  - Location: drawers/masks/mask_png/[drawer_id]/[##]/
  - Filetype: PNG
  - Format: [drawer_id]_[tray_##]_[spec_###].png
    
- FMNH ONLY: CSV file with px-to-mm ratios for each [drawer_id].jpg
  - Location: drawers/fullsize/capture_metadata/sizeratios.csv
  - Filetype: CSV
  - Fields Used: drawer_id, px_mm_ratio

**Outputs**
- Spreadsheet with length and area for each specimen and whether the image has a mask or not
  - Location: drawers/measurements/
  - Filetype: CSV
  - Format: measurements.csv
  - Fields: full_id, drawer_id, tray_id, longest_px, area_px, mask_ok
    - FMNH-ONLY: spec_length_mm, spec_area_mm2, longest_px, missing_size, bad_size 
- Measurement visualizations
  - Location: drawers/measurements/visuals/[drawer_id]/[##]
  - Filetype: PNG
  - Format: [drawer_id]_[tray_##]_[spec_###]_measured.png

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
# Test environment
python test_process_images.py censor_background
# Full processing
python process_images.py censor_background
```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[##]/
  - Filetype: JPG
  - Format: [drawer_id]_[tray_##]_[spec_###].jpg
- Binary masks (white = filled body-shaped polygon, black = background)
  - Location: drawers/masks/mask_png/[drawer_id]/[##]/
  - Filetype: PNG
  - Format: [drawer_id]_[tray_##]_[spec_###].png

**Outputs**
- Specimen images without whited-out backgrounds
  - Location: drawers/masks/no_background/[drawer_id]/[##]/
  - Filetype: PNG 
  - Format: [drawer_id]_[tray_##]_[spec_###]_masked.png

**Dependencies**
- Crop Specimens from Trays (Step 9)
- Create Binary Mask PNGs (Step 11)

### 15. 🟣 Find Pin Outlines 

**Description**

Uses Roboflow instance segmentation to detect mounting pins in masked specimens.

**Command**
```sh
# Test environment
python test_process_images.py infer_pins
# Full processing
python process_images.py infer_pins
```

**Inputs**
- Masked specimens
 - Location: drawers/masked_specimens/[drawer_id]/[tray_##]/
 - Filetype: PNG files with '_masked' suffix
- Measurement data
 - Location: drawers/data/measurements.csv
 - Filetype: CSV with validation flags

**Outputs**
- Pin segmentation predictions
 - Location: drawers/pin_predictions/[drawer_id]/[tray_##]/
 - Filetype: JSON files
 - Fields: pin segmentation coordinates

**Dependencies**
- Apply Initial Background Mask (Step 14)

### 16. Create Pin-Censored Mask

**Description**

Creates final masks by merging specimen body masks with detected pin locations.

**Command**
```sh
# Test environment
python test_process_images.py create_pinmask
# Full processing
python process_images.py create_pinmask
```

**Inputs**
- Masked specimens
 - Location: drawers/masked_specimens/[drawer_id]/[tray_##]/
 - Filetype: PNG files with '_masked' suffix
- Pin segmentation predictions
 - Location: drawers/pin_predictions/[drawer_id]/[tray_##]/
 - Filetype: JSON files

**Outputs**
- Final masks with pins
 - Location: drawers/final_masks/[drawer_id]/[tray_##]/
 - Filetype: PNG files
 - Format: Original filename with '_fullmask' suffix

**Dependencies**
- Find Pin Outlines (Step 15)

### 17. Create Full Transparencies

**Description**

Creates final specimen images with transparent backgrounds using completed masks.

**Command**
```sh
# Test environment
python test_process_images.py create_transparency
# Full processing
python process_images.py create_transparency
```

**Inputs**
- Individual specimen images
 - Location: drawers/specimens/[drawer_id]/[tray_##]/
 - Filetype: JPG files
- Final masks with pins
 - Location: drawers/final_masks/[drawer_id]/[tray_##]/
 - Filetype: PNG files with '_fullmask' suffix

**Outputs**
- Transparent specimens
 - Location: drawers/transparent/[drawer_id]/[tray_##]/
 - Filetype: PNG files
 - Format: Original filename with '_finalmask' suffix

**Dependencies**
- Create Pin-Censored Mask (Step 16)

### 18. 🟧 Process Specimen Labels

**Description**

Uses Claude to transcribe text from specimen images and extract location inFiletypeion.

**Command**
```sh
# Test environment
python test_process_images.py transcribe_images
# Full processing
python process_images.py transcribe_images
```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[tray_##]/
  - Filetype: JPG files

**Outputs**
- Label transcription data
  - Location: drawers/data/transcribed_labels.csv
  - Filetype: CSV with transcription and location data
  - Fields: filename, transcription, location, transcription metadata

**Dependencies**
- Crop Specimens from Trays (Step 9)

### 19. 🟧 Validate Locations

**Description**

Validates and standardizes location data extracted from specimen labels using Claude.

**Command**
```sh
# Test environment
python test_process_images.py validate_transcription
# Full processing
python process_images.py validate_transcription
```
**Inputs**
- Location transcription CSV file
  - Location: drawers/data/transcribed_locations.csv
  - Filetype: CSV with filename, transcription, and location columns

**Outputs**
- Validated location data
  - Location: drawers/data/validated_locations.csv
  - Filetype: CSV with validation results
  - Fields: filename, validation status, final location, confidence notes

**Dependencies**
- Process Specimen Labels (Step 18)


### 20. 🟧 Process Tray Barcodes

**Description**

Uses Claude to read and validate 5-digit barcodes from tray label images.

**Command**
```sh
# Test environment
python test_process_images.py process_barcodes
# Full processing
python process_images.py process_barcodes
```

**Inputs**
- Cropped barcode images
 - Location: drawers/labels/[drawer_id]/[tray_##]/
 - Filetype: JPG files with '_barcode' suffix

**Outputs**
- Barcode data
 - Location: drawers/data/tray_barcodes.csv
 - Filetype: CSV with barcode data
 - Fields: tray_id, unit_barcode

**Dependencies**
- Crop Tray Label Components (Step 7)

### 21. 🟧 Process Taxonomic Names

**Description**

Uses Claude to extract taxonomic inFiletypeion from tray label images.

**Command**
```sh
# Test environment
python test_process_images.py transcribe_taxonomy
# Full processing
python process_images.py transcribe_taxonomy
```

**Inputs**
- Cropped label images
 - Location: drawers/labels/[drawer_id]/[tray_##]/
 - Filetype: JPG files with '_label' suffix

**Outputs**
- Taxonomic data
 - Location: drawers/data/tray_taxonomy.csv
 - Filetype: CSV with taxonomic data
 - Fields: tray_id, full_transcription, taxonomy, authority

**Dependencies**
- Crop Tray Label Components (Step 7)

### 22. Merge All Data

**Description**

Combines all extracted data (measurements, locations, taxonomy, barcodes) into a single dataset.

**Command**
```sh
# Test environment
python test_process_images.py merge_data
# Full processing
python process_images.py merge_data
```

**Inputs**
- Measurement data
 - Location: drawers/data/measurements.csv
 - Filetype: CSV with specimen measurements
- Location data
 - Location: drawers/data/validated_locations.csv
 - Filetype: CSV with validated locations
- Taxonomic data
 - Location: drawers/data/tray_taxonomy.csv
 - Filetype: CSV with taxonomic inFiletypeion
- Barcode data
 - Location: drawers/data/tray_barcodes.csv
 - Filetype: CSV with unit barcodes
- EMU geocodes
 - Location: drawers/data/emu_geocodes.csv
 - Filetype: CSV with institution geocodes

**Outputs**
- Merged dataset
 - Location: drawers/data/merged_data_timestamp.csv
 - Filetype: CSV with all combined data
 - Fields: specimen ID, measurements, taxonomy, location, validation flags

**Dependencies**
- Measure Specimens (Step 13)
- Validate Locations (Step 19)
- Process Tray Barcodes (Step 20)
- Process Taxonomic Names (Step 21)
