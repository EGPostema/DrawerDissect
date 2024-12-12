# Introduction to DrawerDissect

## :beetle: :scissors: Overview  

DrawerDissect is an AI-powered pipeline that automatically processes whole-drawer images of insect specimens.

It can extract:

📷 Individual specimen photographs

🌈 "Masked" specimens for downstream color analysis

📏 Specimen size data

🌎 Taxonomic ID and broad geolocation

:beetle: Reconstructed specimen-level locations, when visible

<img width="1451" alt="DrawerDissect Pipeline Overview" src="https://github.com/user-attachments/assets/385ecb70-589a-4903-9027-ae876ca2decf" />


📄 [COMING SOON: Read our full article pre-print here!](https://www.authorea.com/)


## 🚀 Quick Start Guide

### Prerequisites
- Python 3.x
- Git
- [Roboflow](https://roboflow.com) account
- [Anthropic](https://console.anthropic.com) account
  
### Options for Models
- [Public FMNH Roboflow Models](#public-fmnh-roboflow-models) ⚠️ This is the default!
- [Create Your Own Roboflow Models](#create-your-own-roboflow-models)
- [DIY Models with Our Training Data](#diy-models-with-our-training-data)

### Installation

1. Create and activate a virtual environment:
```sh
python3 -m venv drawerdissect
source drawerdissect/bin/activate
```

2. Install required packages:
```sh
pip install pandas numpy Pillow opencv-python matplotlib roboflow anthropic aiofiles
```

3. Clone the repository:
```sh
git clone https://github.com/EGPostema/DrawerDissect.git
cd DrawerDissect
```

## 🧪 Processing Our Test Image

### 1. Download Test Image

- [Download our test image](https://drive.google.com/drive/folders/1NHV9MSR-sjmAW43KlyPfSB9Xr5ZTvJFt?usp=drive_link)
- Place it in `DrawerDissect/test/drawers/fullsize`
- Note: The image is LARGE (1.3GB) and may take some time to download

### 2. Configure API Keys
Navigate to the test directory:

```sh
cd test
```

Open `test_process_images.py` and add your API keys:

```sh
ANTHROPIC_KEY = 'YOUR_API_HERE' # replace with your API
API_KEY = 'YOUR_ROBOFLOW_API_HERE' # replace with your API
```

[How to find your Roboflow API key](https://docs.roboflow.com/api-reference/authentication)

[How to find your Anthropic API key](https://docs.anthropic.com/en/api/getting-started)

### 3. Run the Full Test Script
```sh
python test_process_images.py
```

The script will:
1. Process all unprocessed images in the `fullsize` folder
2. Create organized output directories
3. Generate individual specimen images, masks, transparencies, and data

[How to call individual steps](#calling-individual-steps)

## 📷 Processing Your Own Images

<i>- Some short summary here, pay particular attention to how drawers/trays are set-up. 
-Tray labels of some kind are important. 
- Note possible performance differences depending on image quality, specimen size, and specimen type
- All current models are trained mainly on mid/large Coleoptera</i>

### 1. Choose Your Model Approach

You have three options for processing images:

#### A. Use Public FMNH Roboflow Models

The simplest approach - just add your API keys and run!
- Requires Roboflow & Anthropic APIs
- Transcribes tray-level labels (barcodes, taxonomy, or both) when transcription toggles are set to 'Y'

⚠️ **Modify `process_images.py` to Add/Edit the Following:**

```sh
# Replace YOUR_API_HERE, YOUR_ROBOFLOW_API_HERE, and YOUR_WORKSPACE_HERE!

ANTHROPIC_KEY = 'YOUR_API_HERE'
API_KEY = 'YOUR_ROBOFLOW_API_HERE'
WORKSPACE = 'YOUR_WORKSPACE_HERE'
```

```sh
# Transcription toggles, adjust to your drawer imaging set-up
TRANSCRIBE_BARCODES = 'N'  # Default is N; set to Y if your drawer images have trays with barcoded labels
TRANSCRIBE_TAXONOMY = 'Y'  # Default is Y; set to N if your drawer images do NOT have tray labels with species information
```

```sh
# User inputs filled in with our public model names. Version numbers up-to-date as of DEC-12-2024

DRAWER_MODEL_ENDPOINT = 'trayfinder'
DRAWER_MODEL_VERSION = 9
TRAY_MODEL_ENDPOINT = 'beetlefinder'
TRAY_MODEL_VERSION = 8
LABEL_MODEL_ENDPOINT = 'labelfinder'
LABEL_MODEL_VERSION = 4
MASK_MODEL_ENDPOINT = 'bugmasker-base'
MASK_MODEL_VERSION = 1
PIN_MODEL_ENDPOINT = 'pinmasker'
PIN_MODEL_VERSION = 5
```

#### B. Create Your Own Roboflow Models

[coming soon] Link to roboflow documentation. 
- Make sure that 5 key models are present (3 obj detection, 2 segmentation) and there is some OCR method.
- Requires Roboflow & Anthropic APIs as-is

#### C. Build Custom Models Using Our Training Data 
[Coming Soon] Access our training data and annotations through Google Drive to build your own models. 
- Can also recommend other open-source methods for OCR!

### 3. Prepare Your Images

1. Place all images in the `fullsize` folder
2. Requirements:
   - Use .jpg format (code can be modified for other formats)
   - Use a consistent naming convention
   - Avoid dashes in filenames (use underscores instead)

**Example Naming Convention:**
At FMNH, we use: `[row]_[cabinet]_[position]` (e.g., "63_5_8" for row 63, cabinet 5, position 8)

The script organizes outputs based on your image names:
- For a drawer image named `DRAWERID.jpg`:
  - Tray images: `DRAWERID_tray_01.jpg`
    - Specimens: `DRAWERID_tray_01_001.jpg`

### 4. Run the Processing Script 

⚠️ **Before running the script, make sure that you have:**
- Cloned the repository
- Created a virtual environment with the required packages
- Navigated to the `DrawerDissect` directory
- Decided on a model approach
- Modified `process_images.py` with ALL required user inputs

```sh
python process_images.py
```

The script will:
1. Process all unprocessed images in the `fullsize` folder
2. Create organized output directories
3. Generate individual specimen images, masks, transparencies, and data

## 🛠️ Calling Individual Steps

Each step can be run individually using either the test script or the full processing script. Choose your command based on whether you're testing (`test_process_images.py`) or processing your own images (`process_images.py`).

### Model Configuration Notes

🟣 **Roboflow Model Steps:**
- Customize confidence and overlap percentages (0-100) when applicable
- Default is 50% for both settings
- Confidence = only annotations the model is over [X]% sure about will be recorded.
- Overlap (obj. detection only) = the model expects object bounding boxes to overlap by up to [X]%.

🟧 **Anthropic OCR Steps:**
- Uses Claude API for text recognition
- Prompts can be edited as-needed in `ocr_header.py`, `ocr_label.py`, and `ocr_validation.py`

### 1. Resize Drawer Images
Test:
```sh
python test_process_images.py resize_drawers
```
Full:
```sh
python process_images.py resize_drawers
```

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

## Summary

[Coming Soon]

## Tips & Troubleshooting

[Coming Soon]
