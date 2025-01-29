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
- [Python 3.x](https://www.python.org/downloads/)
- [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) (not needed if downloading DrawerDissect directly)
- [Roboflow account](https://roboflow.com) (for default script)
- [Anthropic account](https://console.anthropic.com) (for default script)
- Images! (tif, png, or jpg)

### Installation

<ins>For Mac</ins>: enter the commands in **Terminal**

<ins>For Windows</ins>: enter the commands in **PowerShell**

1. **Clone the DrawerDissect repository:**

   ```bash
   git clone https://github.com/EGPostema/DrawerDissect.git
   ```
   **OR directly download and unzip the DrawerDissect repository:**

   <img width="459" alt="Screenshot 2025-01-14 at 11 48 02 AM" src="https://github.com/user-attachments/assets/e60c552f-3aa3-4f17-adc7-09befeb28787" />

   ❗ If downloading directly, be sure to change the filename from `DrawerDissect-main` to `DrawerDissect`


2. **Navigate to the Repository**
 
  ```bash
  cd /path/to/DrawerDissect #replace with your path
  ```

   Your path will depend on where the repository was downloaded to.

3. **Set up a Virtual Environment:**

   ```bash
   python -m venv drawerdissect
   ```

   **Activate Environment (Mac)**

   ```sh
   source drawerdissect/bin/activate
    ```
   
   **Activate Environment (Windows Powershell)**

   ```powershell
   .\drawerdissect\Scripts\activate
    ```
   
4. **Install required packages:**

   ```bash
   pip install pandas numpy Pillow opencv-python matplotlib roboflow anthropic aiofiles
   ```

### Custom Pipelines / Calling Individual Steps

[See: Advanced Options](https://github.com/EGPostema/DrawerDissect?tab=readme-ov-file#-advanced-options)

---

## 🧪 Process Test Image

This is a good place to start to see how the pipeline works!

### Step 0: Ensure you are in `DrawerDissect`

  ```bash
  cd /path/to/DrawerDissect #replace with your path
  ```

Your path will depend on where the repository was downloaded to.

### Step 1: Download the Test Image

[Download test image here!](https://drive.google.com/drive/folders/1NHV9MSR-sjmAW43KlyPfSB9Xr5ZTvJFt?usp=drive_link)

Place the image in `drawers/fullsize`

<img width="353" alt="Screenshot 2025-01-15 at 11 45 44 AM" src="https://github.com/user-attachments/assets/1743ff86-f64a-469d-9722-942868ae096d" />

### Step 2: Configure API Keys

Edit `process_images.py` and replace placeholders with your API keys:


   ```sh
   # Replace YOUR_API_HERE and YOUR_ROBOFLOW_API_HERE
   
   ANTHROPIC_KEY = 'YOUR_API_HERE'
   API_KEY = 'YOUR_ROBOFLOW_API_HERE'
   ```


- [Get Roboflow API key](https://docs.roboflow.com/api-reference/authentication)
- [Get Anthropic API key](https://docs.anthropic.com/en/api/getting-started)

### Step 3: Tailor the Pipeline

Edit `process_images.py` to set specific models and toggles:

   **Use Specialized Model for Masking**

   ```sh
   MASK_MODEL_ENDPOINT = 'bugmasker-tigerbeetle' # replace 'bugmasker-base' with this model
   MASK_MODEL_VERSION = 11  # use version 11
   ```

   **Set PROCESS_METADATA to Y**
   ```sh
   # Default is N; set to Y for test image
   PROCESS_METADATA = 'Y'
   ```

   **Set PIPELINE_MODE to FMNH**
   ```sh
   # Replace 'Default' with 'FMNH' for test image
   PIPELINE_MODE = 'FMNH'
   ```

**Your final edited script should look like this** (changes indicated with arrows):

<img width="550" alt="Screenshot 2025-01-14 at 1 17 02 PM" src="https://github.com/user-attachments/assets/6d85767a-63b6-4609-8051-d88df7201890" />


### Step 4: Run the Script

Execute the script:

  ```bash
  python process_images.py all
  ```

This will:
- Start the processing pipeline on the test image in `fullsize`
- Automatically generate all outputs and directories
- Skip any images that have already been processed (no overwriting)

### Example Outputs

**Generated Directory** 🗂️

<img width="668" alt="Screenshot 2025-01-14 at 4 20 30 PM" src="https://github.com/user-attachments/assets/2a5261ff-0de3-48d9-85ad-4ca4f5fe7559" />

📷 **Individual Tray Images** 

<img width="666" alt="Screenshot 2025-01-14 at 4 22 16 PM" src="https://github.com/user-attachments/assets/8bb72f93-bea3-4eaf-b28f-2caa7ee06ce1" />

📷 **Individual Specimen Images** 

<img width="678" alt="Screenshot 2025-01-14 at 4 37 46 PM" src="https://github.com/user-attachments/assets/937673ef-f733-468b-b016-7b8b87998ec3" />

📏 **Measurement CSV + Sample Size Visualizations**

<img width="660" alt="Screenshot 2025-01-21 at 3 19 56 PM" src="https://github.com/user-attachments/assets/f3c354d3-8fd6-4990-9f3f-c4d8197d0380" />

🏁 **Binary Masks**

<img width="670" alt="Screenshot 2025-01-15 at 8 49 05 PM" src="https://github.com/user-attachments/assets/0752cad1-a299-4dff-9e8c-5e19fcff20cb" />

📷 **Specimen Transparencies**

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

## 📷 Processing Your Own Images

### Step 0: Ensure you are in `DrawerDissect`

  ```bash
  cd /path/to/DrawerDissect #replace with your path
  ```

Your path will depend on where the repository was downloaded to.

### Step 1: Image Preparation

1. **Input images:**
   - Place drawer images in the `drawers/fullsize` folder.
   - JPG format only ❗ [currently updating code to work with tifs/pngs]
   - A consistent drawer naming scheme is helpful for keeping things organized.

2. **Adjust Settings for Your Drawer Configuration (if needed):**
    - Standard FMNH drawers contain **unit trays** with labels (see below)
    - By default, DrawerDissect crops and transcribes:
      - **barcodes**
      - **taxonomic IDs**

<img width="800" alt="Screenshot 2024-12-16 at 3 44 59 PM" src="https://github.com/user-attachments/assets/387e6413-375f-401a-a258-ffb46f6286e4" />

  **For different drawer setups, simply adjust `process_images.py`:**

  **<ins>Trays with barcode AND/OR taxonomy:</ins>**

  ```python
  TRANSCRIBE_BARCODES = 'Y' #default setting, switch to 'N' if no barcodes
  TRANSCRIBE_TAXONOMY = 'Y' #default setting, switch to 'N' if no taxonomy
  ```

  **<ins>Trays with NO LABELS:</ins>**
  ```python
  TRANSCRIBE_BARCODES = 'N'
  TRANSCRIBE_TAXONOMY = 'N'
  ```
  
  Additionally, for better performance, use the non-label trayfinder model:
  
  ```python
   DRAWER_MODEL_ENDPOINT = 'trayfinder-base' #switch from trayfinder-labeled to trayfinder-base
   DRAWER_MODEL_VERSION = 1 
  ```
  
### Step 2. Choose Your Model Approach

You have three options for processing images:

---

#### 1️⃣ **Use Public FMNH Roboflow Models** (⭐ DEFAULT, RECOMMENDED)

- Model names/versions are pre-filled  
- All toggles are set to default  
- Only requires Roboflow & Anthropic API inputs  

**Simply Input APIs in `process_images.py`:**  
```sh
# Replace YOUR_API_HERE and YOUR_ROBOFLOW_API_HERE

ANTHROPIC_KEY = 'YOUR_API_HERE'
API_KEY = 'YOUR_ROBOFLOW_API_HERE'
```

**All FMNH Models (⭐ = default)**

   | Model Name            | Description   | Current Version   | mAP |
   | --------------------- | ------------- | ----------------- | --- |
   | trayfinder-base | detects trays in drawers  | 1 | 99.5% |
   | ⭐ trayfinder-labels  | detects trays (with tray labels) in drawers  | 17 | 99.5% |
   | ⭐ labelfinder  | detects tray label components  | 5 | 98.1% |
   | ⭐ bugfinder-kdn9e | detects specimens  | 9 | 86.8% |
   | ⭐ bugmasker-base | outlines specimen bodies (not taxon specific)  | 9 | 97.5% |
   | bugmasker-tigerbeetle | outlines specimen bodies (specailized)  | 11 | 98.1% |
   | bugmasker-pimeliinae | outlines specimen bodies (specialized)  | 1 | 98.2% |
   | ⭐ pinmasker | outlines specimen pins | 5 | 94.7% |

   Table is up-to-date as of: **1/24/2025**
   
#### 2️⃣ **Create Your Own Roboflow Models**

You can integrate your own custom Roboflow models into DrawerDissect by:  
- Creating a [Roboflow account](https://roboflow.com)  
- Annotating and training models with your own images  
- Editing `process_images.py`:  

```sh
ANTHROPIC_KEY = 'YOUR_API_HERE' # replace with your Anthropic API key
API_KEY = 'YOUR_ROBOFLOW_API_HERE' # replace with your Roboflow API key
WORKSPACE = 'YOUR_WORKSPACE' # replace 'field-museum' with your workspace ID

# Edit these model inputs:
DRAWER_MODEL_ENDPOINT = 'your_model'  # replace with your desired object detection model
DRAWER_MODEL_VERSION = 1  # add version number
TRAY_MODEL_ENDPOINT = 'your_model'  # replace with your desired object detection model
TRAY_MODEL_VERSION = 1  # add version number
LABEL_MODEL_ENDPOINT = 'your_model'  # replace with your desired object detection model
LABEL_MODEL_VERSION = 1  # add version number
MASK_MODEL_ENDPOINT = 'your_model'  # replace with your desired segmentation model
MASK_MODEL_VERSION = 1  # add version number
PIN_MODEL_ENDPOINT = 'your_model'  # replace with your desired segmentation model
PIN_MODEL_VERSION = 1  # add version number
```

[How to get your project ID / version in Roboflow](https://docs.roboflow.com/api-reference/workspace-and-project-ids)

---

#### 3️⃣ **Use Open-Source Models with Our Training Data** ❗ [Coming Soon]

Our pipeline currently relies on **Roboflow** (for object detection/segmentation) and **Anthropic** (for text transcription), which require paid accounts. However, many **free, open-source** AI models exist for image processing and transcription. While we don’t yet support an easy toggle between methods, you’re welcome to modify our code to integrate open-source alternatives!

##### 🔧 **What You’d Need to Modify**
**Roboflow-dependent scripts** (object detection & segmentation):

   `infer_drawers`, `infer_trays`, `infer_beetles`, `infer_labels`, `infer_pins`
   
**Anthropic-dependent scripts** (OCR/transcription):

   `ocr_header`, `ocer_label`, `ocr_validation`
   
**Other adjustments**
  - Our **cropping and mask-generation scripts** rely on Roboflow-generated `.json` files
     - These may need modifications for different models' output formats.
  - There will likely be additional dependencies to install
  - Our **main processing script** `process_images.py` will need to be adjusted

##### 🌎 **Possible Open-Source Alternatives**

   | Model Type | Name | Model it Could Replace... |
   | ---------- | --- | ---------- |
   | Detection | YOLOv8 | ROBOFLOW: trayfinder, labelfinder, bugfinder |
   | Detection | Detectron2 | ROBOFLOW: trayfinder, labelfinder, bugfinder |
   | Detection | mmdetection | ROBOFLOW: trayfinder, labelfinder, bugfinder |
   | Detection | TensorFlow Object Detection API | ROBOFLOW: trayfinder, labelfinder, bugfinder |
   | Detection | OpenCV DNN Module | ROBOFLOW: trayfinder, labelfinder, bugfinder |
   | Segmentation | YOLOv8-seg | ROBOFLOW: bugmasker, pinmasker |
   | Segmentation | Detectron2 | ROBOFLOW: bugmasker, pinmasker |
   | Segmentation | DeepLabV3+ | ROBOFLOW: bugmasker, pinmasker |
   | Segmentation | SAM (Segment Anything Model) | ROBOFLOW: bugmasker, pinmasker |
   | Segmentation | OpenCV GrabCut | ROBOFLOW: bugmasker, pinmasker |
   | Transcription (OCR) | TrOCR (Transformer OCR) | ANTHROPIC: steps that transcribe taxonomy/barcode |
   | Transcription (OCR) | Tesseract OCR | ANTHROPIC: steps that transcribe taxonomy/barcode |
   | Transcription (OCR) | EasyOCR | ANTHROPIC: steps that transcribe taxonomy/barcode |
   | Large Language (LLM) | LLaVa | ANTHROPIC: steps that transcribe & reconstruct label locations |

##### 📂 **Train Your Own Models with Our Data**
- We provide **all FMNH model training data** for you to build custom models.
- Access the data here: ❗ [COMING SOON]
- Data structure details: ❗ [COMING SOON]


### Step 3. Run the Processing Script 

   ```bash
   python process_images.py all
   ```

   The script will:
   - Process images in `fullsize`
   - Create organized output directories
   - Generate specimen images, masks, and a merged dataset
   - Skip any images that have already been processed (no overwriting)

  ❗ **Script not working? Check that you have...**
  - [x] Cloned or downloaded the repository
  - [x] Navigated to the `DrawerDissect` directory
  - [x] Created and activated a virtual environment with the required packages
  - [x] Decided on a model approach 
  - [x] Edited (and saved) `process_images.py` accordingly

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

#### Example 2: Specimen Detection and Cropping Only

For simply detecting and cropping individual specimens from images.

1. Add image(s) with multiple specimens to `drawers/trays`
2. [Modify process_images.py with your API keys](#step-2-choose-your-model-approach)
4. Run the command:

```sh
python process_images.py infer_trays crop_specimens
```

#### Example 3: FMNH Only - Get Pixel:MM Ratios from GIGAMacro Metadata

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
python process_images.py all
```

---

## 📋 Troubleshooting

❗ [coming soon]
