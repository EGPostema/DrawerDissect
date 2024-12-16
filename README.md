# Introduction to DrawerDissect  :beetle: :scissors: 

## 📖 Overview  

**DrawerDissect is an AI-driven pipeline that automatically processes whole-drawer images of insect specimens.**

<i>We created this tool to assist anyone that works with large volumes of preserved insects, particularly in Museums.</I>

<ins>It can extract:</ins>

📷 Individual specimen photos

📏 Specimen size data

:beetle: Taxonomic information

🌈 "Masked" specimens for downstream analysis (ImageJ compatable)

🌎 Broad geolocation + reconstructed specimen-level location (when visible)

<img width="1451" alt="DrawerDissect Pipeline Overview" src="https://github.com/user-attachments/assets/385ecb70-589a-4903-9027-ae876ca2decf" />

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
- Process all unprocessed images in the `fullsize` folder
- Create organized output directories
- Generate individual specimen images, masks, transparencies, and data

[How to call individual steps](#-calling-individual-steps)

[Calling combinations of steps](#-calling-combinations-of-steps)

[Expected outputs](#-summary-and-outputs)

## 📷 Processing Your Own Images

### 1. Whole-Drawer Image Configuration

**Field Museum Drawers**
- FMNH drawers contain **unit trays**.
- All specimens within a given unit tray have the same:
- Tray labels are **top-down visible** for proper detection / transcription.

<div>
  <img src="https://github.com/user-attachments/assets/66393033-3481-4a5a-ac9e-28565fd8b55d" width="300">
  <img src="https://github.com/user-attachments/assets/6ae70348-f612-48e2-bc27-1353f11941ec" width="300">
</div>

**FMNH Unit Tray Label Components**

<img width="300" src="https://github.com/user-attachments/assets/71cc48a2-ed38-41a8-b39f-2c488ad02112" />


**Recommendation for Other Users** 
- Ideally, drawers should have a **visually distinct** way of **organizing specimens into taxonomic units**.
- Other organizational methods **may require one of these modified approaches:**

#### I. If drawers have **unit trays with taxon labels**, but **no barcodes...**

- Open process_images.py
- Adjust the Transcription Toggles:

```sh
# Copy and paste these transcription settings!

TRANSCRIBE_BARCODES = 'N'  
TRANSCRIBE_TAXONOMY = 'Y'  
```

Proceed to [Step 2, Choose Your Model Approach](#-2-choose-your-model-approach)

#### II. If drawers have **unit trays with barcoded labels**, but **no taxonomic information...**

- Open process_images.py
- Adjust the Transcription Toggles:

```sh
# Copy and paste these transcription settings!

TRANSCRIBE_BARCODES = 'Y'  
TRANSCRIBE_TAXONOMY = 'N'  
```

Proceed to [Step 2, Choose Your Model Approach](#-2-choose-your-model-approach)

#### III. If drawers have **unit trays** but **no labels...**

See [3. Example: No Unit Tray Labels](#-3-example-no-unit-tray-labels)

#### IV. If drawers have **no unit trays or subdivisions of any kind...**

[coming soon - use modified version of beetlefinder & script that looks at whole images?]
  
### 2. Choose Your Model Approach

You have three options for processing images:

#### I. Use Public FMNH Roboflow Models (⚠️ DEFAULT)

The simplest approach - just add your API keys!
- Requires Roboflow & Anthropic APIs
- Model names and versions are pre-filled by defaults
- Modify these parts of `process_images.py`:

**API Inputs**
```sh
# Replace YOUR_API_HERE, YOUR_ROBOFLOW_API_HERE, and YOUR_WORKSPACE_HERE!

ANTHROPIC_KEY = 'YOUR_API_HERE'
API_KEY = 'YOUR_ROBOFLOW_API_HERE'
WORKSPACE = 'YOUR_WORKSPACE_HERE'
```

#### II. Create Your Own Roboflow Models

[coming soon] Link to roboflow documentation. 
- Make sure that 5 key models are present (3 obj detection, 2 segmentation) and there is some OCR method.
- Requires Roboflow & Anthropic APIs as-is

#### III. Build Custom Models Using Our Training Data 
[Coming Soon] Access our training data and annotations through Google Drive to build your own models. 
- Can also recommend other open-source methods for OCR
- Note that processing script would have to be substantially modified
- List specific function scripts that would also need to be modified

### 2. Prepare Your Images

- Place all whole-drawer images in the `fullsize` folder
- Use .jpg format (though code could be modified to accept other formats)
- Use a consistent naming convention!

**Example Naming Convention:**

At FMNH, we use: `[row]_[cabinet]_[position]` (e.g., "63_5_8" for row 63, cabinet 5, position 8)

The script organizes outputs based on your image names:
- For a drawer image named `DRAWERID.jpg`:
  - Tray images: `DRAWERID_tray_01.jpg`...
    - Specimens: `DRAWERID_tray_01_spec_001.jpg`...

### 3. Run the Processing Script 

⚠️ **Before running the script, make sure that you have:** ⚠️
- Cloned the repository
- Created a virtual environment with the required packages
- Navigated to the `DrawerDissect` directory
- Decided on a model approach
- Modified `process_images.py` according to your approach

**Run the Command**

```sh
python process_images.py
```

The script will:
- Process all unprocessed images in the `fullsize` folder
- Create organized output directories
- Generate individual specimen images, masks, transparencies, and data

[How to call individual steps](#-calling-individual-steps)

[Calling combinations of steps](#-calling-combinations-of-steps)

[Expected outputs](#-summary-and-outputs)

## 🔧 Calling Individual Steps

Each step can be run individually using either the test script or the full processing script. 

**[For a detailed summary of EACH STEP and how to call them, click here!](https://github.com/EGPostema/DrawerDissect/blob/main/functions/functions_README.md)**

## 🛠 Calling Combinations of Steps

You can call unique combinations of steps by simply adding steps to the basic processing command.

```sh
python test_process_images.py step_1 step_2 step_3...
```

Pick steps from this list:

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

⚠️ **NOTE**: Many steps hinge on the output of previous steps. Make sure you know the [required inputs/outputs to combine them properly.](https://github.com/EGPostema/DrawerDissect/blob/main/functions/functions_README.md)

### 1. Example: Specimen-Only Pipeline

You may have a full set of **individual specimen photos** you want masked, measured, and turned into transparent PNGs.

To do this:

1. Add all specimen images to `drawers/specimens`
2. [Modify process_images.py with your API keys](#2-choose-your-model-approach)
3. Run the command below
   
```sh
python process_images.py infer_beetles create_masks fix_mask process_and_measure_images censor_background infer_pins create_pinmask create_transparency transcribe_images
```

### 2. Example: No Label Reconstruction

You may already have existing metadata for your specimens, making the label reconstruction step is unnecessary.

To run the script without label reconstruction:

1. Add your whole-drawer image(s) to `drawers/fullsize` as usual
2. [Modify process_images.py with your API keys](#2-choose-your-model-approach)
3. Run the command below

```sh
python process_images.py resize_drawers process_metadata infer_drawers crop_trays resize_trays infer_labels crop_labels infer_trays crop_specimens infer_beetles create_masks fix_mask process_and_measure_images censor_background infer_pins create_pinmask create_transparency process_barcodes transcribe_taxonomy
```

### 3. Example: No Unit Tray Labels

If your unit trays do not have **visible labels**, you can run the script without label detection/transcription.

To run the script on drawers without unit tray labels:

1. Add your whole-drawer image(s) to `drawers/fullsize` as usual
2. [Modify process_images.py with your API keys](#2-choose-your-model-approach)
3. Run the command below

```sh
python process_images.py resize_drawers process_metadata infer_drawers crop_trays resize_trays infer_trays crop_specimens infer_beetles create_masks fix_mask process_and_measure_images censor_background infer_pins create_pinmask create_transparency
```

## 📝 Summary and Outputs

[Coming Soon]

## ❗ Tips & Troubleshooting

[Coming Soon]
