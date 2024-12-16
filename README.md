# DrawerDissect :beetle: :scissors:

**DrawerDissect** is an AI-driven pipeline that automates the processing of whole-drawer images of insect specimens. It extracts individual specimen photos, measures specimen size, retrieves taxonomic information, and creates "masked" specimens for downstream analysis.

---

## 📖 Overview

This tool is ideal for those handling large volumes of preserved insects, particularly in museums. DrawerDissect extracts:

- 📷 Individual specimen photos
- 📏 Specimen size data
- 🐞 Taxonomic information
- 🌈 Masked specimens (ImageJ compatible)
- 🌎 Broad geolocation + specimen-level location (when visible)

<img width="1451" alt="Pipeline Overview" src="https://github.com/user-attachments/assets/385ecb70-589a-4903-9027-ae876ca2decf" />

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.x
- Git
- [Roboflow](https://roboflow.com) account
- [Anthropic](https://console.anthropic.com) account
  
### Options for Models
- [Public FMNH Roboflow Models](#public-fmnh-roboflow-models) ⚠️ DEFAULT
- [Create Your Own Roboflow Models](#create-your-own-roboflow-models)
- [DIY Models with Our Training Data](#diy-models-with-our-training-data)

### Installation

1. **Set up a virtual environment:**
   ```bash
   python3 -m venv drawerdissect
   source drawerdissect/bin/activate
   ```

2. **Install required packages:**
   ```bash
   pip install pandas numpy Pillow opencv-python matplotlib roboflow anthropic aiofiles
   ```

3. **Clone the repository:**
   ```bash
   git clone https://github.com/EGPostema/DrawerDissect.git
   cd DrawerDissect
   ```

---

## 🧪 Processing Test Images

### Step 1: Download the Test Image
- [Download test image](https://drive.google.com/drive/folders/1NHV9MSR-sjmAW43KlyPfSB9Xr5ZTvJFt?usp=drive_link)
- Place it in `DrawerDissect/test/drawers/fullsize`
  
**Note:** The test image is large and may take some time to download.

### Step 2: Configure API Keys

Edit `test_process_images.py` and replace placeholders with your API keys:

```python
ANTHROPIC_KEY = 'YOUR_API_HERE'
API_KEY = 'YOUR_ROBOFLOW_API_HERE'
```

- [Get Roboflow API key](https://docs.roboflow.com/api-reference/authentication)
- [Get Anthropic API key](https://docs.anthropic.com/en/api/getting-started)

### Step 3: Run the Test Script

Execute the script:

```bash
python test_process_images.py
```

This will:
- Process the image in `fullsize`
- Generate output directories
- Create specimen images, masks, and data

---

## 📷 Processing Your Images

### Step 1: Image Preparation

1. **Organize images:**
   - Place drawer images in the `fullsize` folder.
   - Use `.jpg` format with a consistent naming convention.

   **FMNH Example:** `row_cabinet_position` (e.g., `63_5_8.jpg`).

<img width="800" alt="Screenshot 2024-12-16 at 3 44 59 PM" src="https://github.com/user-attachments/assets/387e6413-375f-401a-a258-ffb46f6286e4" />

2. **Adjust Unit Tray Settings (if needed):**
    - Standard FMNH drawers contain **unit trays** with labels (see above)
    - All specimens in a tray share a **barcode**, **qr code**, **geocode**, and **taxonomic unit**
    - By default DrawerDissect crops and transcribes **barcode** and **taxonomy**
    - For different setups, adjust toggles in `process_images.py`:

   **Trays with <ins>barcodes only</ins>:**
   ```python
   TRANSCRIBE_BARCODES = 'Y'
   TRANSCRIBE_TAXONOMY = 'N'
   ```

   **Trays with <ins>taxonomy only</ins>:**
   ```python
   TRANSCRIBE_BARCODES = 'N'
   TRANSCRIBE_TAXONOMY = 'Y'
   ```

    **Trays with <ins>no label</ins>:**
    See [Example: No Unit Tray Labels](#3-example-no-unit-tray-labels)


### Step 2. Choose Your Model Approach

You have three options for processing images:

1. **Use Public FMNH Roboflow Models** ⚠️ DEFAULT

    - Model names/versions are pre-filled
    - Requires Roboflow & Anthropic APIs
    - Modify `process_images.py`:
  
    **API Inputs**
    ```sh
    # Replace YOUR_API_HERE and YOUR_ROBOFLOW_API_HERE
    
    ANTHROPIC_KEY = 'YOUR_API_HERE'
    API_KEY = 'YOUR_ROBOFLOW_API_HERE'
    ```

2. **Create Your Own Roboflow Models**

    [coming soon] Link to roboflow documentation. 
    - Make sure that key models are present (3 obj detection, 2 segmentation) + an OCR method.
    - Requires Roboflow & Anthropic APIs as-is

3. **Build Custom Models Using Our Training Data**

    [coming Soon] Access our training data and annotations through Google Drive to build your own models. 
    - Can also recommend other open-source methods for OCR
    - Note that processing script would have to be substantially modified
    - List specific function scripts that would also need to be modified

### Step 3. Run the Processing Script 

   ```bash
   python process_images.py
   ```

   The script will:
   - Process images in `fullsize`
   - Create organized output directories
   - Generate specimen images, masks, and data

  ❗ **Script not working? Check that you have...**
  - [x] Cloned the repository
  - [x] Created a virtual environment with the required packages
  - [x] Navigated to the `DrawerDissect` directory
  - [x] Decided on a model approach 
  - [x] Modified `process_images.py` accordingly

---

## 🔧 Advanced Options

### Calling Individual Steps

You can run specific steps of the pipeline individually:

```bash
python test_process_images.py step_1
```

**Steps Available:**

```sh
resize_drawers
process_metadata
infer_drawers
crop_trays
resize_trays
infer_labels
crop_labels
infer_trays
crop_specimens
infer_beetles
create_masks
fix_mask
process_and_measure_images
censor_background
infer_pins
create_pinmask
create_transparency
transcribe_images
validate_transcription
process_barcodes
transcribe_taxonomy
merge_data
```

### Custom Pipelines

#### Example 1: Specimen-Only Pipeline

If you have a set of **individual specimen photos** you want masked, measured, and turned into transparent PNGs:

1. Add all specimen images to `drawers/specimens`
2. [Modify process_images.py with your API keys](#step-2-choose-your-model-approach)
3. Run the command:
   
```sh
python process_images.py infer_beetles create_masks fix_mask process_and_measure_images censor_background infer_pins create_pinmask create_transparency transcribe_images
```

#### Example 2: No Label Reconstruction

If you have existing metadata for your specimens or simply don't want to reconstruct labels:

1. Add your whole-drawer image(s) to `drawers/fullsize` as usual
2. [Modify process_images.py with your API keys](#step-2-choose-your-model-approach)
3. Run the command:

```sh
python process_images.py resize_drawers process_metadata infer_drawers crop_trays resize_trays infer_labels crop_labels infer_trays crop_specimens infer_beetles create_masks fix_mask process_and_measure_images censor_background infer_pins create_pinmask create_transparency process_barcodes transcribe_taxonomy
```

#### Example 3: No Unit Tray Labels

If your unit trays do not have **visible labels**:

1. Add your whole-drawer image(s) to `drawers/fullsize` as usual
2. [Modify process_images.py with your API keys](#step-2-choose-your-model-approach)
3. Run the command:

```sh
python process_images.py resize_drawers process_metadata infer_drawers crop_trays resize_trays infer_trays crop_specimens infer_beetles create_masks fix_mask process_and_measure_images censor_background infer_pins create_pinmask create_transparency
```

#### Example 4: FMNH Only - Get Pixel:MM Ratios from GIGAMacro Metadata

If you are capturing whole drawers with a GIGAMacro Magnify2 system:

1. Add your whole-drawer image(s) to `drawers/fullsize` as usual
2. Add matching metadata TXT files to `drawers/fullsize/capture_metadata`
3. [Modify process_images.py with your API keys](#step-2-choose-your-model-approach)
4. Set metadata toggle to 'Y'

```sh
# Metadata toggle (Default is N; set to Y for FMNH users with Gigamacro TXT files)
PROCESS_METADATA = 'Y'
```
5. Run the command:
```sh
python process_images.py
```

---

## 📋 Outputs and Tips

- Outputs are saved in structured directories based on image names.
- Consult [functions_README.md](https://github.com/EGPostema/DrawerDissect/blob/main/functions/functions_README.md) for a detailed guide to pipeline steps.
