# Introduction to DrawerDissect

## 🪲 🔍 Overview

DrawerDissect is an AI-powered pipeline that automatically processes whole-drawer images of insect specimens. It extracts:
- Individual specimen photographs
- Specimen "masks" for phenotypic analysis
- Taxonomic information
- Partial or full geographic location

<img width="1451" alt="DrawerDissect Pipeline Overview" src="https://github.com/user-attachments/assets/385ecb70-589a-4903-9027-ae876ca2decf" />


📄 [Read our full article pre-print here!](https://www.authorea.com/)

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.x
- Git
- [Roboflow](https://roboflow.com) account
- [Anthropic](https://console.anthropic.com) account
  
**Options for Models**
- [Public FMNH Roboflow Models](#public-fmnh-roboflow-models) ⚠️ This is the default
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
- ⚠️ Note: The image is 1.3GB and may take time to download

### 2. Configure API Keys
Navigate to the test directory:

```sh
cd test
```

Open `test_process_images.py` and add your API keys:

<img width="317" alt="Screenshot 2024-12-12 at 10 30 57 AM" src="https://github.com/user-attachments/assets/e1c03cc3-3948-4cba-bc3f-2d3a466ab27b" />

- **Replace YOUR_API_HERE with <u>your Anthropic API KEY</u>**
- **Replace YOUR_ROBOFLOW_API_HERE with <u>your Roboflow API key</u>**

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

### 4. Call Individual Steps

Any of the steps can be called individually.

🟣 <span style="color: #800080">Purple steps use **Roboflow Models**.</span>
- You can personalize your desired % confidence and overlap for each model.
- The default is set to 50% for each - this  works well for most models, but can be changed by changing to 50 to any number between 0 and 100. 
- "50% confidence": only annotations the model is over 50% sure about will be recorded in the coordinates file.
- "50% overlap":the model expects that different objects in the JPG image have bounding boxes around them that overlap by up to 50%.

🟧 <span style="color: #FF8C00">Orange steps use **Claude Anthropic for OCR**.</span>

1. **Resize Drawer Images**

```sh 
python test_process_images.py resize_drawers
```

2. **Calculate Pixel:MM Ratios from Metadata**

```sh 
python test_process_images.py process_metadata
```

3. 🟣 <span style="color: #800080">**Find Tray Coordinates**</span>


```sh 
python test_process_images.py infer_drawers --drawer_confidence 50 --drawer_overlap 50
```

Modify confidence or overlap % by changing 50 to any number 1-100.

4. **Crop Trays from Drawers**

```sh 
python test_process_images.py crop_trays
```

5. **Resize Trays**

```sh 
python test_process_images.py resize_trays
```

6. 🟣 <span style="color: #800080">**Find Tray Label Coordinates**</span>

```sh 
python test_process_images.py infer_labels --label_confidence 50 --label_overlap 50
```

Modify confidence or overlap % by changing 50 to any number 1-100.

7. **Crop Tray Label Components**

```sh 
python test_process_images.py crop_labels
```

8. 🟣 <span style="color: #800080">**Find Specimen Coordinates**</span>

```sh 
python test_process_images.py infer_trays --tray_confidence 50 --tray_overlap 50
```

Modify confidence or overlap % by changing 50 to any number 1-100. 50% is default.

9. **Crop Specimens from Trays**

```sh 
python test_process_images.py crop_specimens
```

10. 🟣 <span style="color: #800080">**Find Specimen Body Outlines**</span>

```sh 
python test_process_images.py infer_beetles --beetle_confidence 50
```

Modify confidence % by changing 50 to any number 1-100. 50% is default.

11. **Create Binary Mask PNGs from Outlines**

```sh 
python test_process_images.py create_masks
```

12. **Fix Masks with Multiple Polygons**

```sh 
python test_process_images.py fix_mask
```

13. **Measure Specimen Length and Area**

```sh 
python test_process_images.py process_and_measure_images
```

14. **Apply Initial Mask to Specimens (Removes Background)**

```sh 
python test_process_images.py censor_background
```

16. 🟣 <span style="color: #800080">**Find Pin Outlines**</span>

```sh 
python test_process_images.py infer_pins
```

17. **Create Binary Mask PNG with Pin Censored**

```sh 
python test_process_images.py create_pinmask
```

18. **Create Fully Masked Specimen Transparencies**

```sh 
python test_process_images.py create_transparency
```

19. 🟧 <span style="color: #FF8C00">**Reconstruct Locations from Specimen Labels**</span>

```sh 
python test_process_images.py transcribe_images
```

20. 🟧 <span style="color: #FF8C00">**Cross-Check Location Validity**</span>

```sh 
python test_process_images.py validate_transcription
```

21. 🟧 <span style="color: #FF8C00">**Transcribe Tray Barcode Numbers**</span>

```sh 
python test_process_images.py process_barcodes
```

22. 🟧 <span style="color: #FF8C00">**Transcribe Tray Taxonomic Names**</span>

```sh 
python test_process_images.py transcribe_taxonomy
```

23. **Merge All Datasets**

```sh 
python test_process_images.py merge_data
```

## ⚡ Processing Your Own Images

<i>WIP!</i>

### 1. Choose Your Model Approach

You have three options for processing your images:

#### A. Use Public FMNH Roboflow Models + Anthropic
The simplest approach - just add your API keys and update the version number if needed.

<i>show image here of all user inputs and what needs to be changed</i>

#### B. Create Your Own Roboflow Models 🟣
To use your own models, you'll need to configure:

**Workspace ID**
Find this in your Roboflow workspace settings:
<img width="807" alt="Roboflow Workspace Settings" src="https://github.com/EGPostema/DrawerDissect/assets/142446286/19016e31-2542-48b5-9e51-7372de3e5b90">

**Model Name and Version**
Locate these in your Roboflow project:
1. Go to Projects > Select your model > Versions
2. Select your desired version
3. Find the model info as shown:
<img width="782" alt="Roboflow Model Version" src="https://github.com/EGPostema/DrawerDissect/assets/142446286/e2918f19-9867-42d1-ae20-53369f2d4018">

Configure your model in the script:
<img width="486" alt="Model Configuration Example" src="https://github.com/EGPostema/DrawerDissect/assets/142446286/1070e844-ab02-4c6a-a605-bdf781498f62">

**Note:** Model names should be lowercase, using underscores or no spaces. Version numbers can be easily updated as you train better models.

#### C. Build Custom Models Using Our Training Data 🟣
[Coming Soon] Access our training data and annotations through Google Drive to build your own models.

### 3. Prepare Your Images

1. Place all images in the `fullsize` folder
2. Requirements:
   - Use .jpg format (code can be modified for other formats)
   - Use a consistent naming convention
   - Avoid dashes in filenames (use underscores instead)

**Example Naming Convention:**
At FMNH, we use: `[row]_[cabinet]_[position]` (e.g., "63_5_8" for row 63, cabinet 5, position 8)

<img width="461" alt="Folder Structure Example" src="https://github.com/EGPostema/DrawerDissect/assets/142446286/c6526924-908f-4999-af55-8c89962b2518">

The script organizes outputs based on your image names:
- For a drawer image named `DRAWERID.jpg`:
  - Tray images: `DRAWERID_tray_01.jpg`
  - Specimens: `DRAWERID_tray_01_001.jpg`

### 4. Run the Processing Script 

**Make sure you are in the `DrawerDissect` directory before running the script!**

```sh
python process_images.py
```

The script will:
1. Process all unprocessed images in the `fullsize` folder
2. Create organized output directories
3. Generate individual specimen images and data



