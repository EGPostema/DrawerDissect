# DrawerDissect :beetle: :scissors:

**DrawerDissect** is an AI-driven pipeline that automates the processing of whole-drawer images of insect specimens. It extracts individual specimen photos, measures specimen size, retrieves taxonomic information, and creates "masked" specimens for downstream analysis.

---

## 📖 Overview

DrawerDissect is ideal for digitizing large volumes of preserved insects, particularly from natural history collections. It can extract:

- 📷  Individual specimen photos
- 📏  Specimen size data
- 🐞  Taxonomic information
- 🌈  Masked specimens (ImageJ compatible)
- 🌎  Broad geolocation + specimen-level location (when visible)

<img width="800" alt="DrawerDissect whole-drawer processing pipeline" src="https://github.com/user-attachments/assets/a5b2d71b-a9e0-4494-854d-d790957c82b0" />

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.x
- Git
- [Roboflow account](https://roboflow.com) (for default script)
- [Anthropic account](https://console.anthropic.com) (for default script)
  
### Options for Models

See [all options here.](#step-2-choose-your-model-approach)

### Installation

1. **Set up a virtual environment:**
   ```bash
   python3 -m venv drawerdissect
   ```

   **Active Environment (Mac)**

   ```sh
   source drawerdissect/bin/activate
    ```
   
   **Activate Environment (Windows Powershell)**

   ```powershell
   .\drawerdissect\Scripts\activate
    ```

   **Activate Environment (Windows CMD)**

   ```cmd
   drawerdissect\Scripts\activate.bat
    ```
   
3. **Install required packages:**
   ```bash
   pip install pandas numpy Pillow opencv-python matplotlib roboflow anthropic aiofiles
   ```

4. **Clone the repository:**
   ```bash
   git clone https://github.com/EGPostema/DrawerDissect.git
   cd DrawerDissect
   ```

---

## 🧪 Processing Test Images

### Step 0: Navigate to `test`

  ```bash
  cd test
  ```

### Step 1: Download the Test Image
- [Download test image](https://drive.google.com/drive/folders/1NHV9MSR-sjmAW43KlyPfSB9Xr5ZTvJFt?usp=drive_link)
- Place it in `DrawerDissect/test/drawers/fullsize`
  
❗ The test image is large and may take some time to download.

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

### Example Outputs

[show images of outputs here]

---

## 📷 Processing Your Own Images

### Step 0: Navigate to `DrawerDissect`

   ```bash
   cd DrawerDissect
   ```

### Step 1: Image Preparation

1. **Organize images:**
   - Place drawer images in the `fullsize` folder.
   - Use `.jpg` format with a consistent naming convention.

   **FMNH Example:** `row_cabinet_position` (e.g., `63_5_8.jpg`).

2. **Adjust Unit Tray Settings (if needed):**
    - Standard FMNH drawers contain **unit trays** with labels (see below)
    - All specimens in a tray share a:
      - **barcode**
      - **qr code**
      - **geocode**
      - **taxonomic ID**
    - By default, DrawerDissect crops and transcribes:
      - **barcodes**
      - **taxonomic IDs**

<img width="800" alt="Screenshot 2024-12-16 at 3 44 59 PM" src="https://github.com/user-attachments/assets/387e6413-375f-401a-a258-ffb46f6286e4" />

  **For different setups, simply adjust the toggles in `process_images.py`:**

  **<ins>Trays with barcodes only:</ins>**
  ```python
  TRANSCRIBE_BARCODES = 'Y'
  TRANSCRIBE_TAXONOMY = 'N'
  ```

  **<ins>Trays with taxonomy only:</ins>**
  ```python
  TRANSCRIBE_BARCODES = 'N'
  TRANSCRIBE_TAXONOMY = 'Y'
  ```

  **<ins>Trays with no header labels:</ins>**
  ```python
  TRANSCRIBE_BARCODES = 'N'
  TRANSCRIBE_TAXONOMY = 'N'
  ```

  Also see: [Example 3: No Unit Tray Labels](https://github.com/EGPostema/DrawerDissect#example-3-no-unit-tray-labels)
  
### Step 2. Choose Your Model Approach

You have three options for processing images:

1. **Use Public FMNH Roboflow Models** ⚠️ DEFAULT

    - Model names/versions are pre-filled
    - Requires Roboflow & Anthropic APIs

    **To begin, modify APIs for `process_images.py`:**
  
    ```sh
    # Replace YOUR_API_HERE and YOUR_ROBOFLOW_API_HERE
    
    ANTHROPIC_KEY = 'YOUR_API_HERE'
    API_KEY = 'YOUR_ROBOFLOW_API_HERE'
    ```

2. **Create Your Own Roboflow Models**

    ❗ [coming soon] Link to roboflow documentation. 
    - Make sure that key models are present (3 obj detection, 2 segmentation) + an OCR method.
    - Requires Roboflow & Anthropic APIs as-is

3. **Build Custom Models Using Our Training Data**

    ❗ [coming Soon] Access our training data and annotations through Google Drive to build your own models. 
    - Can also recommend other open-source methods for OCR
    - Processing script would have to be substantially modified
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

You can run specific steps of the pipeline individually, e.g.:

```bash
python process_images.py resize_drawers
```

**Steps Available:**

```sh
resize_drawers
```
```sh
#FMNH / GIGAMacro Only
process_metadata
```
```sh
infer_drawers
```
```sh
crop_trays
```
```sh
resize_trays
```
```sh
infer_labels
```
```sh
crop_labels
```
```sh
infer_trays
```
```sh
crop_specimens
```
```sh
infer_beetles
```
```sh
create_masks
```
```sh
fix_mask
```
```sh
process_and_measure_images
```
```sh
censor_background
```
```sh
infer_pins
```
```sh
create_pinmask
```
```sh
create_transparency
```
```sh
transcribe_images
```
```sh
validate_transcription
```
```sh
process_barcodes
```
```sh
transcribe_taxonomy
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

❗ [coming soon]
