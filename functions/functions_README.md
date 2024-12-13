## ⚙️ Summary of Processing Steps

Below, we list all steps used in the processing script, with the following information:
- A short description
- Inputs and outputs
- Single-step command
- Visual aids
- Model type, if applicable
  - 🟣 = roboflow
  - 🟧 = anthropic

### Model Configuration Notes

🟣 **Roboflow Model Steps**
- Customize confidence and overlap percentages (0-100) when applicable
- Default is 50% for both settings
- Confidence = only annotations the model is over [X]% sure about will be recorded.
- Overlap (obj. detection only) = the model expects object bounding boxes to overlap by up to [X]%.

🟧 **Anthropic OCR Steps**
- Uses Claude API for text recognition
- Prompts can be edited as-needed in `ocr_header.py`, `ocr_label.py`, and `ocr_validation.py`

### 1. Resize Drawer Images

**Description**
Resizes full-size drawer images to create 1000px-wide versions ready for inference.

**Command**
```sh
# Test environment
python test_process_images.py resize_drawers
# Full processing
python process_images.py resize_drawers
```

**Inputs**
- Whole-size drawer images
  - Location: drawers/fullsize/
  - Format: JPG

**Outputs**

- Resized drawer images
  - Location: drawers/resized/
  - Format: JPG files
  - Naming: drawer filename with '_1000' suffix
  - Example: drawer1.jpg → drawer1_1000.jpg

**Dependencies**
- No prior steps required (this is typically the first step)

### 2. Calculate Size Ratios from Metadata
**Description**
Calculates pixel-to-millimeter conversion ratios from drawer metadata for accurate measurements.

**Command**
```sh
# Test environment
python test_process_images.py process_metadata
# Full processing
python process_images.py process_metadata
```

**Inputs**
- Metadata text files
  - Location: drawers/metadata/
  - Format: TXT files with GIGAMacro system specifications
- Original drawer images
  - Location: drawers/fullsize/
  - Format: JPG

**Outputs**
- Measurement conversion data
  - Location: drawers/data/drawer_measurements.csv
  - Format: CSV with drawer dimensions and conversion ratios
  - Fields: drawer_id, image dimensions (px/mm), px_mm_ratio

**Dependencies**
- No prior steps required

### 3. 🟣 Find Tray Coordinates
**Description**
Uses Roboflow object detection to locate drawer unit trays in resized images.

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
 - Format: JPG files with '_1000' suffix

**Outputs**
- Tray coordinate predictions
 - Location: drawers/drawer_predictions/
 - Format: JSON files with coordinate data
 - Fields: predictions, image info, time_taken

**Dependencies**
- Resized Drawer Images (from Step 1)

### 4. Crop Trays from Drawers
**Description**
Crops individual unit trays from full-size drawer images using coordinate predictions.

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
 - Format: JPG
- Tray coordinate predictions
 - Location: drawers/drawer_predictions/
 - Format: JSON files

**Outputs**
- Individual tray images
 - Location: drawers/trays/[drawer_id]/
 - Format: JPG files
 - Naming: drawer_id_tray_##.jpg

**Dependencies**
- Find Tray Coordinates (Step 3)

### 5. Resize Trays
**Description**
Creates 1000px-wide versions of cropped tray images for processing.

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
 - Format: JPG files

**Outputs**
- Resized tray images
 - Location: drawers/trays_resized/[drawer_id]/
 - Format: JPG files
 - Naming: original filename with '_1000' suffix

**Dependencies**
- Crop Trays from Drawers (Step 4)

### 6. 🟣 Find Tray Label Coordinates
**Description**
Uses Roboflow object detection to locate barcodes, geocodes, and labels within tray images.

**Command**
```sh
# Test environment
python test_process_images.py infer_labels --label_confidence 50 --label_overlap 50
# Full processing
python process_images.py infer_labels --label_confidence 50 --label_overlap 50
```

**Inputs**
- Resized tray images
 - Location: drawers/trays_resized/[drawer_id]/
 - Format: JPG files with '_1000' suffix

**Outputs**
- Label coordinate predictions
 - Location: drawers/label_predictions/
 - Format: JSON files with '_label' suffix
 - Fields: predictions for barcode, geocode, label, qr classes

**Dependencies**
- Resize Trays (Step 5)

### 7. Crop Tray Label Components
**Description**
Extracts individual label components (barcodes, geocodes, text labels) from full-size tray images.

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
 - Format: JPG files
- Label coordinate predictions
 - Location: drawers/label_predictions/
 - Format: JSON files

**Outputs**
- Cropped label components
 - Location: drawers/labels/[drawer_id]/[tray_num]/
 - Format: JPG files
 - Naming: [drawer_id]_tray_[##]_[component].jpg

**Dependencies**
- Find Tray Label Coordinates (Step 6)

### 8. 🟣 Find Specimen Coordinates
**Description**
Uses Roboflow object detection to locate individual specimens within tray images.

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
 - Format: JPG files with '_1000' suffix

**Outputs**
- Specimen coordinate predictions
 - Location: drawers/specimen_predictions/
 - Format: JSON files
 - Fields: predictions for each specimen location

**Dependencies**
- Resize Trays (Step 5)

### 9. Crop Specimens from Trays
**Description**
Extracts individual specimens from full-size tray images in a top-to-bottom, left-to-right order.

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
 - Format: JPG files
- Specimen coordinate predictions
 - Location: drawers/specimen_predictions/
 - Format: JSON files

**Outputs**
- Individual specimen images
 - Location: drawers/specimens/[drawer_id]/[tray_num]/
 - Format: JPG files
 - Naming: [drawer_id]_tray_[##]_spec_[###].jpg

**Dependencies**
- Find Specimen Coordinates (Step 8)

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
 - Location: drawers/specimens/[drawer_id]/[tray_num]/
 - Format: JPG files

**Outputs**
- Specimen segmentation predictions
 - Location: drawers/beetle_predictions/[drawer_id]/[tray_num]/
 - Format: JSON files
 - Fields: segmentation mask coordinates

**Dependencies**
- Crop Specimens from Trays (Step 9)

### 11. Create Binary Mask PNGs
**Description**
Converts specimen segmentation predictions into binary mask images.


**Command**
```sh
# Test environment
python test_process_images.py create_masks
# Full processing
python process_images.py create_masks
```

**Inputs**
- Specimen segmentation predictions
 - Location: drawers/beetle_predictions/[drawer_id]/[tray_num]/
 - Format: JSON files with segmentation coordinates

**Outputs**
- Binary masks
 - Location: drawers/masks/[drawer_id]/[tray_num]/
 - Format: PNG files (black and white)
 - Naming: Same as specimen filename with .png extension

**Dependencies**
- Find Specimen Body Outlines (Step 10)

### 12. Fix Multi-Polygon Masks
**Description**
Ensures each mask contains only one connected component by keeping the largest polygon.

**Command**
```sh
# Test environment
python test_process_images.py fix_mask
# Full processing
python process_images.py fix_mask
```

**Inputs**
- Binary masks
 - Location: drawers/masks/[drawer_id]/[tray_num]/
 - Format: PNG files

**Outputs**
- Fixed binary masks
 - Location: Same as input
 - Format: PNG files
 - Modification: Only largest connected component retained

**Dependencies**
- Create Binary Mask PNGs (Step 11)

### 13. Measure Specimens
**Description**
Calculates specimen dimensions using binary masks and pixel-to-mm ratios.

**Command**
```sh
# Test environment
python test_process_images.py process_and_measure_images
# Full processing
python process_images.py process_and_measure_images
```

**Inputs**
- Binary masks
 - Location: drawers/masks/[drawer_id]/[tray_num]/
 - Format: PNG files
- Drawer measurement data
 - Location: drawers/data/drawer_measurements.csv
 - Format: CSV with px_mm_ratio

**Outputs**
- Measurement data
 - Location: drawers/data/measurements.csv
 - Format: CSV with length and area measurements
 - Fields: specimen ID, dimensions in px and mm
- Measurement visualizations
 - Location: drawers/measurements/visuals/
 - Format: PNG files showing contours and measurements

**Dependencies**
- Fix Multi-Polygon Masks (Step 12)
- Calculate Pixel:MM Ratios (Step 2)

### 14. Apply Initial Background Mask
**Description**
Creates initial masked specimens by applying body segmentation masks to remove backgrounds.

**Command**
```sh
# Test environment
python test_process_images.py censor_background
# Full processing
python process_images.py censor_background
```

**Inputs**
- Individual specimen images 
 - Location: drawers/specimens/[drawer_id]/[tray_num]/
 - Format: JPG files
- Binary masks
 - Location: drawers/masks/[drawer_id]/[tray_num]/
 - Format: PNG files
- Measurement data
 - Location: drawers/data/measurements.csv
 - Format: CSV with validation flags

**Outputs**
- Masked specimens
 - Location: drawers/masked_specimens/[drawer_id]/[tray_num]/
 - Format: PNG files
 - Naming: Original filename with '_masked' suffix

**Dependencies**
- Measure Specimens (Step 13)

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
 - Location: drawers/masked_specimens/[drawer_id]/[tray_num]/
 - Format: PNG files with '_masked' suffix
- Measurement data
 - Location: drawers/data/measurements.csv
 - Format: CSV with validation flags

**Outputs**
- Pin segmentation predictions
 - Location: drawers/pin_predictions/[drawer_id]/[tray_num]/
 - Format: JSON files
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
 - Location: drawers/masked_specimens/[drawer_id]/[tray_num]/
 - Format: PNG files with '_masked' suffix
- Pin segmentation predictions
 - Location: drawers/pin_predictions/[drawer_id]/[tray_num]/
 - Format: JSON files

**Outputs**
- Final masks with pins
 - Location: drawers/final_masks/[drawer_id]/[tray_num]/
 - Format: PNG files
 - Naming: Original filename with '_fullmask' suffix

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
 - Location: drawers/specimens/[drawer_id]/[tray_num]/
 - Format: JPG files
- Final masks with pins
 - Location: drawers/final_masks/[drawer_id]/[tray_num]/
 - Format: PNG files with '_fullmask' suffix

**Outputs**
- Transparent specimens
 - Location: drawers/transparent/[drawer_id]/[tray_num]/
 - Format: PNG files
 - Naming: Original filename with '_finalmask' suffix

**Dependencies**
- Create Pin-Censored Mask (Step 16)

### 18. 🟧 Process Specimen Labels
**Description**
Uses Claude to transcribe text from specimen images and extract location information.

**Command**
```sh
# Test environment
python test_process_images.py transcribe_images
# Full processing
python process_images.py transcribe_images
```

**Inputs**
- Individual specimen images
  - Location: drawers/specimens/[drawer_id]/[tray_num]/
  - Format: JPG files

**Outputs**
- Label transcription data
  - Location: drawers/data/transcribed_labels.csv
  - Format: CSV with transcription and location data
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
  - Format: CSV with filename, transcription, and location columns

**Outputs**
- Validated location data
  - Location: drawers/data/validated_locations.csv
  - Format: CSV with validation results
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
 - Location: drawers/labels/[drawer_id]/[tray_num]/
 - Format: JPG files with '_barcode' suffix

**Outputs**
- Barcode data
 - Location: drawers/data/tray_barcodes.csv
 - Format: CSV with barcode data
 - Fields: tray_id, unit_barcode

**Dependencies**
- Crop Tray Label Components (Step 7)

### 21. 🟧 Process Taxonomic Names
**Description**
Uses Claude to extract taxonomic information from tray label images.

**Command**
```sh
# Test environment
python test_process_images.py transcribe_taxonomy
# Full processing
python process_images.py transcribe_taxonomy
```

**Inputs**
- Cropped label images
 - Location: drawers/labels/[drawer_id]/[tray_num]/
 - Format: JPG files with '_label' suffix

**Outputs**
- Taxonomic data
 - Location: drawers/data/tray_taxonomy.csv
 - Format: CSV with taxonomic data
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
 - Format: CSV with specimen measurements
- Location data
 - Location: drawers/data/validated_locations.csv
 - Format: CSV with validated locations
- Taxonomic data
 - Location: drawers/data/tray_taxonomy.csv
 - Format: CSV with taxonomic information
- Barcode data
 - Location: drawers/data/tray_barcodes.csv
 - Format: CSV with unit barcodes
- EMU geocodes
 - Location: drawers/data/emu_geocodes.csv
 - Format: CSV with institution geocodes

**Outputs**
- Merged dataset
 - Location: drawers/data/merged_data_[timestamp].csv
 - Format: CSV with all combined data
 - Fields: specimen ID, measurements, taxonomy, location, validation flags

**Dependencies**
- Measure Specimens (Step 13)
- Validate Locations (Step 19)
- Process Tray Barcodes (Step 20)
- Process Taxonomic Names (Step 21)
