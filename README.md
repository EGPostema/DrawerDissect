# DrawerDissect :beetle: :scissors:

**DrawerDissect** is an AI-driven pipeline that automates the processing of whole-drawer images of insect specimens. It extracts individual specimen photos, measures specimen size, retrieves taxonomic information, and creates "masked" specimens for downstream analysis.

---

## 📖 Overview

DrawerDissect is ideal for digitizing large volumes of preserved insects, particularly from natural history collections. It can extract:

- 📷  Individual specimen photos
- 📏  Specimen size data
- 🐞  Taxonomic information
- 🌈  Masked specimens (ImageJ compatible)
- 🌎  Specimen-level location estimates (when visible)

<img width="1000" alt="Screenshot 2025-01-29 at 4 12 05 PM" src="https://github.com/user-attachments/assets/2568c5af-a22b-42b3-b0c5-e070b9995db8" />

---

## 🚀 Quick Start Guide

### Prerequisites

- Python 3.x
- API keys from:
  - [Roboflow](roboflow.com) - for detecting and measuring specimens
  - [Anthropic](anthropic.com) - for reading tray and specimen labels
- Supported image formats: TIF/TIFF, PNG, JPG/JPEG

---

### Installation

1. **Get the Code**
  
  ```bash
  # Using git
  git clone https://github.com/EGPostema/DrawerDissect.git
  ```

  OR, Download the zipped folder directly
  
  <img width="420" alt="Screenshot 2025-02-03 at 5 49 32 PM" src="https://github.com/user-attachments/assets/8b2fe830-f6bc-4c5f-ac32-284ec174887e" />
  
  Unzip, then rename folder from `DrawerDissect-main` to `DrawerDissect`

2. **Setup Environment**

```bash
# Navigate to project folder (change '/your/path/to/')
cd /your/path/to/DrawerDissect
```

```bash
# Create the virtual environment
python -m venv drawerdissect
```

```bash
# Activate environment
source drawerdissect/bin/activate  # Use this command for Mac/Linux
.\drawerdissect\Scripts\activate   # Use this command for Windows
```

```bash
# Install dependencies (be patient, this make take a minute)
pip install pandas numpy Pillow opencv-python matplotlib roboflow anthropic aiofiles pyyaml
```

3. **Configure API Keys**

Open `config.yaml` in the main directory, and add your API keys:

```yaml
api_keys:
  anthropic: "YOUR_ANTHROPIC_KEY" # replace YOUR_ANTHROPIC_KEY with your key
  roboflow: "YOUR_ROBOFLOW_KEY" # replace YOUR_ROBOFLOW_KEY with your key
```

- [Get Anthropic API Key](https://support.anthropic.com/en/articles/8114521-how-can-i-access-the-anthropic-api)
- [Get Roboflow API Key](https://docs.roboflow.com/api-reference/authentication)

This step is <ins>REQUIRED</ins> for all object detection, segmentation, and transcription steps to run.

---

## 🧪 Run the Pipeline

### Start by Processing A Test Image
1. [Download the test image](https://drive.google.com/drive/folders/1NHV9MSR-sjmAW43KlyPfSB9Xr5ZTvJFt?usp=drive_link) (large image, be patient!)
2. Place it in `drawers/fullsize`
3. Check that `config.yaml` contains your API keys
4. Edit `config.yaml` to enable metadata processing

  ```yaml
  processing:
    process_metadata: true # default is false
  ```

Our imaging system produces a metadata .txt file. This file can be used to convert pixel:mm, if process_metadata is toggled on.

5. Edit `config.yaml` to use a more specialized masking model

   ```yaml
    mask:
      endpoint: "bugmasker-tigerbeetle" # replace bugmasker-all with this model
      version: 11 # use most recent version
      confidence: 50

   # all other models can stay the same
   ```

6. Run the Script

  ```bash
  # this command runs all steps in the pipeline
  python process_images.py all
  ```

[Click Here to see Examples of Outputs!](https://github.com/EGPostema/DrawerDissect/blob/main/README.md#-example-outputs)

---

### Process Your Own Images

1. Place drawer images in `drawers/fullsize`
2. Check that `config.yaml` contains your API keys
3. Decide your model approach:

---

#### Option A: Use Public FMNH Roboflow Models (⭐ DEFAULT, RECOMMENDED)

The script is set up to use FMNH models by default, defined in `config.yaml`

```yaml
# Example of how our models are configured

roboflow:
  workspace: "field-museum" # FMNH workspace default, can change to your own
  models:
    drawer:
      endpoint: "trayfinder-labels" # obj detection, drawer to trays
      version: 17
      confidence: 50 
      overlap: 50
```

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

   Any of these models can be swapped in/out as long as workspace is set to `field-museum`

#### Option B: Use Your Own Roboflow Models

You can integrate your own custom Roboflow models into DrawerDissect via the `config.yaml` file:

```yaml
roboflow:
  workspace: "YOUR_WORKSPACE" # Fill in with your own roboflow workspace
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

#### Option C: Use Open-Source Models with Our Training Data

Many **free, open-source** AI models exist for image processing and transcription. While we don’t currently support these architectures, you’re welcome to modify our code to integrate open-source alternatives!

**Possible Free Alternatives**

   | Model Function | Possible Alternatives | Model it Could Replace |
   | ---------- | --- | ---------- |
   | Detection | YOLOv8, Detectron2, mmdetection, TensorFlow Object Detection, OpenCV DNN Module | ROBOFLOW: trayfinder, labelfinder, bugfinder |
   | Segmentation | YOLOv8-seg, Detectron2, DeepLabV3+, SAM (Segment Anything Model), OpenCV GrabCut | ROBOFLOW: bugmasker, pinmasker |
   | Tray Label Transcription | LLaVa, TrOCR (Transformer OCR), Tesseract OCR, EasyOCR | ANTHROPIC |
   | Collection Location Reconstruction | LLaVa | ANTHROPIC |


**We provide all FMNH model training data - feel free to use these to train your own models with your preferred architectures!**
- Access the data here: ❗ [COMING SOON]
- Data structure details: ❗ [COMING SOON]

---

4. Configure the pipeline

Standard FMNH drawers contain **unit trays** with labels (see below)

<img width="800" alt="Screenshot 2024-12-16 at 3 44 59 PM" src="https://github.com/user-attachments/assets/387e6413-375f-401a-a258-ffb46f6286e4" />

By default, DrawerDissect crops and transcribes:
  - **barcodes**
  - **taxonomic IDs**

**For different drawer setups, simply adjust `config.yaml`:**

```yaml
processing:
  process_metadata: false  # Set to true if metadata txt file is present
  transcribe_barcodes: true  # Set to false if no barcodes
  transcribe_taxonomy: true  # Set to false if no taxonomic IDs
```
5. Run the Script

  ```bash
  # this command runs all steps in the pipeline
  python process_images.py all
  ```

---

## 📊 Example Outputs

📷 **Individual Tray Images** 

<img width="666" alt="Screenshot 2025-01-14 at 4 22 16 PM" src="https://github.com/user-attachments/assets/8bb72f93-bea3-4eaf-b28f-2caa7ee06ce1" />

🗺️ **Specimen Location Guides** 

![image](https://github.com/user-attachments/assets/c2d29085-a1f3-4745-814b-9bcc85697a23)

📷 **Individual Specimen Images** 

<img width="678" alt="Screenshot 2025-01-14 at 4 37 46 PM" src="https://github.com/user-attachments/assets/937673ef-f733-468b-b016-7b8b87998ec3" />

📏 **Measurement CSV + 10 Example Size Visualizations**

<img width="660" alt="Screenshot 2025-01-21 at 3 19 56 PM" src="https://github.com/user-attachments/assets/f3c354d3-8fd6-4990-9f3f-c4d8197d0380" />

🏁 **Binary Masks**

<img width="670" alt="Screenshot 2025-01-15 at 8 49 05 PM" src="https://github.com/user-attachments/assets/0752cad1-a299-4dff-9e8c-5e19fcff20cb" />

📷 **Fully Masked Specimens**

<img width="670" alt="Screenshot 2025-01-15 at 10 02 32 AM" src="https://github.com/user-attachments/assets/cdf044a5-e1e2-4cc7-beef-c113cd5cc276" />

📋 **Merged Dataset**

<img width="289" alt="Screenshot 2025-01-15 at 11 49 00 AM" src="https://github.com/user-attachments/assets/889065e9-0f81-46f8-8961-4f87fa042df2" />

<ins>Dataset Fields:</ins>
   - Drawer, Tray, and Specimen-level IDs and filenames
   - Tray-level label text (barcode, taxonomy)
   - Specimen length1/length2 and area
   - Mask/measurement checks
   - Specimen-level location reconstructions, with confidence notes

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
3. Configure `config.yaml` with API keys
4. Run the command:
   
```sh
python process_images.py outline_specimens create_masks fix_masks measure_specimens censor_background outline_pins create_pinmask create_transparency
```

#### Example 2: Specimen Detection and Cropping Only

For simply detecting and cropping individual specimens from images.

1. Create folder `drawers/trays`
2. Add image(s) with multiple specimens to `drawers/trays`
3. Configure `config.yaml` with API keys
4. Run the command:

```sh
python process_images.py find_specimens crop_specimens create_traymaps
```

#### Example 3: Processing Drawers With NO Tray Labels

1. Create folder `drawers/trays`
2. Add drawers to `drawers/trays` instead of `drawers/fullsize`
3. Configure `config.yaml` with API keys
4. Edit config.yaml as follows:

  ```yaml
  # use model that doesn't look for tray labels, if using FMNH models

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
