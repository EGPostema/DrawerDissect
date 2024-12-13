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

### 2. Calculate Pixel:MM Ratios
Test:
```sh
python test_process_images.py process_metadata
```

Full:
```sh
python process_images.py process_metadata
```

### 3. 🟣 Find Tray Coordinates
Test:
```sh
python test_process_images.py infer_drawers --drawer_confidence 50 --drawer_overlap 50
```
Full:
```sh
python process_images.py infer_drawers --drawer_confidence 50 --drawer_overlap 50
```

### 4. Crop Trays from Drawers
Test:
```sh
python test_process_images.py crop_trays
```
Full:
```sh
python process_images.py crop_trays
```

### 5. Resize Trays
Test:
```sh
python test_process_images.py resize_trays
```
Full:
```sh
python process_images.py resize_trays
```

### 6. 🟣 Find Tray Label Coordinates
Test:
```sh
python test_process_images.py infer_labels --label_confidence 50 --label_overlap 50
```
Full:
```sh
python process_images.py infer_labels --label_confidence 50 --label_overlap 50
```

### 7. Crop Tray Label Components
Test:
```sh
python test_process_images.py crop_labels
```
Full:
```sh
python process_images.py crop_labels
```

### 8. 🟣 Find Specimen Coordinates
Test:
```sh
python test_process_images.py infer_trays --tray_confidence 50 --tray_overlap 50
```
Full:
```sh
python process_images.py infer_trays --tray_confidence 50 --tray_overlap 50
```

### 9. Crop Specimens from Trays
Test:
```sh
python test_process_images.py crop_specimens
```
Full:
```sh
python process_images.py crop_specimens
```

### 10. 🟣 Find Specimen Body Outlines
Test:
```sh
python test_process_images.py infer_beetles --beetle_confidence 50
```
Full:
```sh
python process_images.py infer_beetles --beetle_confidence 50
```

### 11. Create Binary Mask PNGs
Test:
```sh
python test_process_images.py create_masks
```
Full:
```sh
python process_images.py create_masks
```

### 12. Fix Multi-Polygon Masks
Test:
```sh
python test_process_images.py fix_mask
```
Full:
```sh
python process_images.py fix_mask
```

### 13. Measure Specimens
Test:
```sh
python test_process_images.py process_and_measure_images
```
Full:
```sh
python process_images.py process_and_measure_images
```

### 14. Apply Initial Background Mask
Test:
```sh
python test_process_images.py censor_background
```
Full:
```sh
python process_images.py censor_background
```

### 15. 🟣 Find Pin Outlines
Test:
```sh
python test_process_images.py infer_pins
```
Full:
```sh
python process_images.py infer_pins
```

### 16. Create Pin-Censored Mask
Test:
```sh
python test_process_images.py create_pinmask
```
Full:
```sh
python process_images.py create_pinmask
```

### 17. Create Full Transparencies
Test:
```sh
python test_process_images.py create_transparency
```
Full:
```sh
python process_images.py create_transparency
```

### 18. 🟧 Process Specimen Labels
Test:
```sh
python test_process_images.py transcribe_images
```
Full:
```sh
python process_images.py transcribe_images
```

### 19. 🟧 Validate Locations
Test:
```sh
python test_process_images.py validate_transcription
```
Full:
```sh
python process_images.py validate_transcription
```

### 20. 🟧 Process Tray Barcodes
Test:
```sh
python test_process_images.py process_barcodes
```
Full:
```sh
python process_images.py process_barcodes
```

### 21. 🟧 Process Taxonomic Names
Test:
```sh
python test_process_images.py transcribe_taxonomy
```
Full:
```sh
python process_images.py transcribe_taxonomy
```

### 22. Merge All Data
Test:
```sh
python test_process_images.py merge_data
```
Full:
```sh
python process_images.py merge_data
```
