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

### Installation

<ins>For Mac</ins>: enter the commands in **Terminal**

<ins>For Windows</ins>: enter the commands in **PowerShell** or **CMD**

1. **Clone the DrawerDissect repository:**

   ```bash
   git clone https://github.com/EGPostema/DrawerDissect.git
   ```
    _Alternatively, simply download and unzip the DrawerDissect repository:_

   <img width="459" alt="Screenshot 2025-01-14 at 11 48 02 AM" src="https://github.com/user-attachments/assets/e60c552f-3aa3-4f17-adc7-09befeb28787" />


3. **Navigate to the Directory**
 
  ```bash
  cd DrawerDissect
  ```

2. **Set up a virtual environment:**

   ```bash
   python3 -m venv drawerdissect
   ```

   **Activate Environment (Mac)**

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
   
4. **Install required packages:**

   ```bash
   pip install pandas numpy Pillow opencv-python matplotlib roboflow anthropic aiofiles
   ```

---

## 🧪 Process Test Image

This is a good place to start to see how the pipeline works!

### Step 0: Ensure you are in `DrawerDissect`

   ```bash
   cd DrawerDissect
   ```

### Step 1: Download the Test Image

[Download test image](https://drive.google.com/drive/folders/1NHV9MSR-sjmAW43KlyPfSB9Xr5ZTvJFt?usp=drive_link)
- ❗ The test image is large and may take some time to download/move

Place the image in `DrawerDissect/drawers/fullsize`

### Step 2: Configure API Keys

Edit `process_images.py` and replace placeholders with your API keys:

  ```python
  ANTHROPIC_KEY = 'YOUR_API_HERE'
  API_KEY = 'YOUR_ROBOFLOW_API_HERE'
  ```

- [Get Roboflow API key](https://docs.roboflow.com/api-reference/authentication)
- [Get Anthropic API key](https://docs.anthropic.com/en/api/getting-started)

### Step 3: Configure Step Toggles

Edit `process_images.py` to tailor the pipeline:

   **Use Specialized Model for Segmentation**

   ```sh
   MASK_MODEL_ENDPOINT = 'bugmasker-tigerbeetle' # replace 'bugmasker-base' with this model
   MASK_MODEL_VERSION = 11  # use version 11
   ```

   **Set Process_Metadata to Y**
   ```sh
   # Metadata toggle (Default is N; set to Y for test image)
   PROCESS_METADATA = 'Y'
   ```

### Step 4: Run the Test Script

Execute the script:

  ```bash
  python process_images.py
  ```

This will:
- Process the image in `fullsize`
- Generate output directories
- Create specimen images, masks, and data

### Example Outputs

❗ [coming soon]

---

## 📷 Processing Your Own Images

### Step 0: Ensure you are in `DrawerDissect`

   ```bash
   cd DrawerDissect
   ```

### Step 1: Image Preparation

1. **Input images:**
   - Place drawer images in the `fullsize` folder.
   - Use `.jpg` format.
   - A consistent drawer naming format is best for keeping things organized.

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

  **For different drawer setups, simply adjust the toggles in `process_images.py`:**

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

I. **Use Public FMNH Roboflow Models** (DEFAULT)

    - Model names/versions are pre-filled
    - Only requires Roboflow & Anthropic APIs

    ** Just modify APIs for `process_images.py`:**
  
    ```sh
    # Replace YOUR_API_HERE and YOUR_ROBOFLOW_API_HERE
    
    ANTHROPIC_KEY = 'YOUR_API_HERE'
    API_KEY = 'YOUR_ROBOFLOW_API_HERE'
    ```

II. **Create Your Own Roboflow Models** ❗ [coming soon]

    - Link to roboflow documentation. 
    - Make sure that key models are present (3 obj detection, 2 segmentation) + an OCR method.
    - Requires Roboflow & Anthropic APIs as-is

III. **Build Custom Models Using Our Training Data** ❗ [coming soon]

    - Access our training data and annotations through Google Drive to build your own models. 
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
  - [x] Cloned or downloaded the repository
  - [x] Navigated to the `DrawerDissect` directory
  - [x] Created a virtual environment with the required packages
  - [x] Decided on a model approach 
  - [x] Modified (and saved) `process_images.py` accordingly

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
process_metadata # FMNH / GIGAMacro Only
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
process_barcodes # if trays have barcodes
transcribe_taxonomy # if trays have taxonomic info
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
