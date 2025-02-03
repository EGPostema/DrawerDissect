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

<img width="1000" alt="Screenshot 2025-01-29 at 4 12 05 PM" src="https://github.com/user-attachments/assets/2568c5af-a22b-42b3-b0c5-e070b9995db8" />

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.x
- Git (optional - only needed if cloning repository)
- [Roboflow account & API key](roboflow.com), for object detection and segmentation
- [Anthropic account & API key](anthropic.com), for transcription
- Image formats: TIF/TIFF, PNG, JPG/JPEG

---

### Installation

#### Step 1: Get the Code
**Option A: Clone Repository**
```bash
git clone https://github.com/EGPostema/DrawerDissect.git
```

**Option B: Download Directly**
1. Download and unzip from GitHub
2. Rename folder from `DrawerDissect-main` to `DrawerDissect`

#### Step 2: Setup Environment
Navigate to project folder:
```bash
cd path/to/DrawerDissect
```

Create and activate virtual environment:
```bash
# Create environment
python -m venv drawerdissect

# Activate environment
## For Mac/Linux:
source drawerdissect/bin/activate
## For Windows (PowerShell):
.\drawerdissect\Scripts\activate
```

Install dependencies:
```bash
pip install pandas numpy Pillow opencv-python matplotlib roboflow anthropic aiofiles pyyaml
```

---

### Configuration

#### Step 1. Open the `config.yaml` file

This file comes pre-filled and is in the main directory, `DrawerDissect`.

#### Step 2. Update API Keys
Modify `config.yaml` with API keys - this is **required** for all object detection, segmentation, and transcription steps!
```yaml
api_keys:
  anthropic: "YOUR_ANTHROPIC_KEY"  # Required
  roboflow: "YOUR_ROBOFLOW_KEY"    # Required
```
- [Get Anthropic API Key](https://support.anthropic.com/en/articles/8114521-how-can-i-access-the-anthropic-api)
- [Get Roboflow API Key](https://docs.roboflow.com/api-reference/authentication)

#### Step 3. Pipeline Settings
These are the default pipeline settings. Default settings work for most cases, so no need to alter these (unless desired).
```yaml
processing:
  process_metadata: false  # Only set to true if you have GIGAMacro metadata .txt files or similar
  transcribe_barcodes: true  # Set to false if no barcoded labels
  transcribe_taxonomy: true  # Set to false if no taxonomic labels
```

#### Step 4. Roboflow Model Settings
By default, the script works with public `field-museum` models created in Roboflow. All models and versions are pre-filled.
```yaml
# Example of how models are configured
roboflow:
  workspace: "field-museum"
  models:
    drawer:
      endpoint: "trayfinder-labels"  # obj detection, Drawer → Trays (with tray labels)
      version: 17 # most recent version
```
[DETAILED instructions on alternate model options](https://github.com/EGPostema/DrawerDissect/blob/main/README.md#step-2-choose-your-model-approach)

---

### Running the Script

- [With a Test Image](https://github.com/EGPostema/DrawerDissect/blob/main/README.md#-process-test-image)
- [With Your Own Images](https://github.com/EGPostema/DrawerDissect/blob/main/README.md#-process-your-own-images)
- [Custom Pipelines & Running Individual Steps](https://github.com/EGPostema/DrawerDissect/blob/main/README.md#step-3-choose-your-model-approach)

---

## 🧪 Process Test Image

This is a good place to start to see how the pipeline works, using an example drawer from the FMNH collection.

### Navigate to `DrawerDissect`

  ```bash
  cd /path/to/DrawerDissect
  ```

### Download the Test Image

[Download test image here!](https://drive.google.com/drive/folders/1NHV9MSR-sjmAW43KlyPfSB9Xr5ZTvJFt?usp=drive_link)

Place the image in `drawers/fullsize`

<img width="353" alt="Screenshot 2025-01-15 at 11 45 44 AM" src="https://github.com/user-attachments/assets/1743ff86-f64a-469d-9722-942868ae096d" />

### Configuration

#### Step 1. Open the `config.yaml` file

This file comes pre-filled and is in the main directory, `DrawerDissect`.

#### Step 2. Update API Keys

Modify `config.yaml` with API keys - this is **required** for all object detection, segmentation, and transcription steps!
```yaml
api_keys:
  anthropic: "YOUR_ANTHROPIC_KEY"  # Required
  roboflow: "YOUR_ROBOFLOW_KEY"    # Required
```
- [Get Anthropic API Key](https://support.anthropic.com/en/articles/8114521-how-can-i-access-the-anthropic-api)
- [Get Roboflow API Key](https://docs.roboflow.com/api-reference/authentication)

#### Step 3: Update Pipeline Settings

Edit `config.yaml` in the following places:

   **Use Tiger Beetle-specific Mask Model**

   ```yaml
    mask:
      endpoint: "bugmasker-tigerbeetle" # replace bugmasker-all with this model
      version: 11 # use most recent version
      confidence: 50

   # all other models can stay the same
   ```

   **Turn On Metadata Processing**

   The metadata .txt file for the test image comes pre-downloaded in `drawers/fullsize/capture_metadata`
      - Setting `process_metadata` to `true` will use this file to convert pixels to mm when measuring specimens

   ```yaml
   processing:
     process_metadata: true  # Change from false to true
   ```

### Run the Script

Start processing with the command:

  ```bash
  python process_images.py all
  ```

This will:
- Start the processing pipeline on the test image in `fullsize`
- Automatically generate all outputs and directories
- Skip any images that have already been processed (no overwriting)

---

### Example Outputs

**Generated Directory** 🗂️

<img width="668" alt="Screenshot 2025-01-14 at 4 20 30 PM" src="https://github.com/user-attachments/assets/2a5261ff-0de3-48d9-85ad-4ca4f5fe7559" />

📷 **Individual Tray Images** 

<img width="666" alt="Screenshot 2025-01-14 at 4 22 16 PM" src="https://github.com/user-attachments/assets/8bb72f93-bea3-4eaf-b28f-2caa7ee06ce1" />

🗺️ **Specimen Location Maps** 

![image](https://github.com/user-attachments/assets/c2d29085-a1f3-4745-814b-9bcc85697a23)

📷 **Individual Specimen Images** 

<img width="678" alt="Screenshot 2025-01-14 at 4 37 46 PM" src="https://github.com/user-attachments/assets/937673ef-f733-468b-b016-7b8b87998ec3" />

📏 **Measurement CSV + Sample Size Visualizations**

<img width="660" alt="Screenshot 2025-01-21 at 3 19 56 PM" src="https://github.com/user-attachments/assets/f3c354d3-8fd6-4990-9f3f-c4d8197d0380" />

🏁 **Binary Masks**

<img width="670" alt="Screenshot 2025-01-15 at 8 49 05 PM" src="https://github.com/user-attachments/assets/0752cad1-a299-4dff-9e8c-5e19fcff20cb" />

📷 **Fully Masked Specimens (transparent & white background versiosn)**

<img width="670" alt="Screenshot 2025-01-15 at 10 02 32 AM" src="https://github.com/user-attachments/assets/cdf044a5-e1e2-4cc7-beef-c113cd5cc276" />

📋 **Merged Dataset**

<img width="289" alt="Screenshot 2025-01-15 at 11 49 00 AM" src="https://github.com/user-attachments/assets/889065e9-0f81-46f8-8961-4f87fa042df2" />

<ins>Dataset Fields:</ins>
   - Drawer, Tray, and Specimen-level IDs and filenames
   - Tray-level label text (barcode, taxonomy)
   - Specimen length1/length2 and area (in pixels & mm)
   - Mask/measurement checks
   - Specimen-level location reconstructions, with confidence notes

---

## 📷 Process Your Own Images

### Navigate to `DrawerDissect`

  ```bash
  cd /path/to/DrawerDissect
  ```

### Add Images

Place drawer images in the `drawers/fullsize` folder.
   - Supported formats: tif/tiff, png, jpg/jpeg

### Drawer Configuration

#### Step 1. Open the `config.yaml` file

This file comes pre-filled and is in the main directory, `DrawerDissect`.

#### Step 2. Adjust Transcription Toggles

Standard FMNH drawers contain **unit trays** with labels (see below)
    - By default, DrawerDissect crops and transcribes:
      - **barcodes**
      - **taxonomic IDs**

<img width="800" alt="Screenshot 2024-12-16 at 3 44 59 PM" src="https://github.com/user-attachments/assets/387e6413-375f-401a-a258-ffb46f6286e4" />

  **For different drawer setups, simply adjust `config.yaml`:**

  ```yaml
processing:
  transcribe_barcodes: true  # Set false if no barcodes
  transcribe_taxonomy: true  # Set false if no taxonomic IDs
  ```
  
#### Step 3. Choose Your Model Approach

You have three options for processing images:

---

##### Option A: Use Public FMNH Roboflow Models (⭐ DEFAULT, RECOMMENDED)

The script is set up to use FMNH models (pre-filled in the config file) by default. 

**Simply Input Your API Keys in `config.yaml`:**  
```yaml
api_keys:
  anthropic: "YOUR_ANTHROPIC_KEY"  # Required
  roboflow: "YOUR_ROBOFLOW_KEY"    # Required
```
- [Get Anthropic API Key](https://support.anthropic.com/en/articles/8114521-how-can-i-access-the-anthropic-api)
- [Get Roboflow API Key](https://docs.roboflow.com/api-reference/authentication)

**All Available FMNH Models (⭐ = default)**

   | Model Name            | Description   | Current Version   | mAP |
   | --------------------- | ------------- | ----------------- | --- |
   | trayfinder-base | detects trays in drawers  | 1 | 99.5% |
   | ⭐ trayfinder-labels  | detects trays (with tray labels) in drawers  | 17 | 99.5% |
   | ⭐ labelfinder  | detects tray label components  | 5 | 98.1% |
   | ⭐ bugfinder-kdn9e | detects specimens  | 9 | 86.8% |
   | ⭐ bugmasker-all | outlines specimen bodies (not taxon specific)  | 2 | 98.2% |
   | bugmasker-tigerbeetle | outlines specimen bodies (specailized)  | 11 | 98.1% |
   | bugmasker-pimeliinae | outlines specimen bodies (specialized)  | 1 | 98.2% |
   | ⭐ pinmasker | outlines specimen pins | 5 | 94.7% |

   Any of these models can be used as long as workspace is set to `field-museum`:

  ```yaml
  roboflow:
    workspace: "field-museum"
  ```
   
##### Option B: Create Your Own Roboflow Models

You can integrate your own custom Roboflow models into DrawerDissect by:  
- Creating a [Roboflow account](https://roboflow.com)  
- Annotating and training models with your own images  
- Fill in the `config.yaml`:  

```yaml
api_keys:
  anthropic: "YOUR_ANTHROPIC_KEY"  # Required
  roboflow: "YOUR_ROBOFLOW_KEY"    # Required

roboflow:
  workspace: "YOUR_WORKSPACE" # Fill in your roboflow workspace
  models:
    drawer:
      endpoint: "DRAWER_TO_TRAY_MODEL" # Fill in with obj detection model here
      version: 1 # version number here
      confidence: 50
      overlap: 50
    tray:
      endpoint: "TRAY_TO_SPECIMEN_MODEL" # Fill in with obj detection model here
      version: 1 # version number here
      confidence: 50
      overlap: 50
    label:
      endpoint: "TRAY_TO_TRAYLABEL_MODEL" # Fill in with obj detection model here
      version: 1 # version number here
      confidence: 50
      overlap: 50
    mask:
      endpoint: "SPECIMEN_MASKING_MODEL" # Fill in with segmentation model here
      version: 1 # version number here
      confidence: 50
    pin:
      endpoint: "PIN_MASKING_MODEL" # Fill in with segmentation model here
      version: 1 # version number here
      confidence: 50
```

[How to get your project ID / version in Roboflow](https://docs.roboflow.com/api-reference/workspace-and-project-ids)

##### Option C: Use Open-Source Models with Our Training Data ❗ [Coming Soon]

Our pipeline currently relies on **Roboflow** (for object detection/segmentation) and **Anthropic** (for text transcription), which require paid accounts. However, many **free, open-source** AI models exist for image processing and transcription. While we don’t yet support an easy toggle between methods, you’re welcome to modify our code to integrate open-source alternatives!

**What Would Need to be Modified**

1. All Roboflow-dependent scripts (object detection & segmentation)
2. All Anthropic-dependent scripts (OCR/transcription)</ins>
3. All cropping and mask-generation scripts rely on Roboflow-generated `.json` files
     - These may need to be modified for different models' output formats
4. The **main processing script** `process_images.py`
5. The **configuration files** `config.yaml` and `config.py`
6. There would likely be additional dependencies to install

**Possible Open-Source Alternatives**

   | Model Function | Possible Alternatives | Model it Could Replace |
   | ---------- | --- | ---------- |
   | Detection | YOLOv8, Detectron2, mmdetection, TensorFlow Object Detection, OpenCV DNN Module | ROBOFLOW: trayfinder, labelfinder, bugfinder |
   | Segmentation | YOLOv8-seg, Detectron2, DeepLabV3+, SAM (Segment Anything Model), OpenCV GrabCut | ROBOFLOW: bugmasker, pinmasker |
   | Tray Label Transcription | LLaVa, TrOCR (Transformer OCR), Tesseract OCR, EasyOCR | ANTHROPIC |
   | Collection Location Reconstruction | LLaVa | ANTHROPIC |


**We provide all FMNH model training data - feel free to use these to train your own custom models!**
- Access the data here: ❗ [COMING SOON]
- Data structure details: ❗ [COMING SOON]


### Run the Script 

   ```bash
   python process_images.py all
   ```

   The script will:
   - Process images in `fullsize`
   - Create organized output directories
   - Generate specimen images, masks, and a merged dataset
   - Skip any images that have already been processed (no overwriting)

---

## 🔧 Advanced Options

### Calling Individual Steps

You can run specific steps of the pipeline individually, e.g.:

```bash
python process_images.py resize_drawers
```

**Steps Available:**

```sh
all # to run full script
resize_drawers
process_metadata # if metadata TXT file present
find_trays
crop_trays
resize_trays
find_traylabels
crop_labels
find_specimens
crop_specimens
create_traymaps
outline_specimens
create_masks
fix_masks
measure_specimens
censor_background
outline_pins
create_pinmask
create_transparency
transcribe_speclabels
validate_speclabels
transcribe_barcodes # if tray labels have barcodes
transcribe_taxonomy # if tray labels have taxonomic IDs
merge_data
```

### Custom Pipelines

#### Example 1: Specimen Masking / Measuring Only

If you have a set of **individual specimen photos** you want masked, measured, and turned into transparent PNGs:

1. Create folder `drawers/specimens`
2. Add all specimen images to `drawers/specimens`
3. Configure config.yaml with API keys
4. Run the command:
   
```sh
python process_images.py outline_specimens create_masks fix_masks measure_specimens censor_background outline_pins create_pinmask create_transparency
```

#### Example 2: Specimen Detection and Cropping Only

For simply detecting and cropping individual specimens from images.

1. Create folder `drawers/trays`
2. Add image(s) with multiple specimens to `drawers/trays`
3. Add API keys to config.yaml
4. Run the command:

```sh
python process_images.py find_specimens crop_specimens create_traymaps
```

#### Example 3: Processing Drawers With NO Tray Labels ❗ (I think I need to edit some scripts to make this work)

1. Create folder `drawers/trays`
2. Add drawers to `drawers/trays` instead of `drawers/fullsize`
3. Add API keys to config.yaml
4. Edit config.yaml as follows:

  ```yaml
  # use trayfinder model that doesn't look for tray labels, if using FMNH models
  models:
    drawer:
      endpoint: "trayfinder-base" # obj detection, drawer to trays
      version: 1
      confidence: 50
      overlap: 50
  ```

```yaml
processing:
  process_metadata: false  # Set to false
  transcribe_barcodes: false  # Set to false
  transcribe_taxonomy: false  # Set to false
```

5. Run the command:

```sh
python process_images.py find_specimens crop_specimens create_traymaps create_traymaps outline_specimens create_masks fix_masks measure_specimens censor_background outline_pins create_pinmask create_transparency transcribe_speclabels validate_speclabels
```

---

## 📋 Troubleshooting

❗ **Script not working? Check that you have...**
  - [x] Cloned or downloaded the repository
  - [x] Navigated to the `DrawerDissect` directory
  - [x] Created and activated a virtual environment with the required packages
  - [x] Decided on a model approach 
  - [x] Edited (and saved) `process_images.py` accordingly

❗ More troubleshooting/tips to come...
