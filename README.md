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
- [Public FMNH Roboflow Models](#public-fmnh-roboflow-models)
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

## Start with Our Test Image

### 1. Download Test Image

- [Download our test image](https://drive.google.com/drive/folders/1NHV9MSR-sjmAW43KlyPfSB9Xr5ZTvJFt?usp=drive_link)
- Place it in `DrawerDissect/test/drawers/fullsize`
- ⚠️ Note: The image is 1.3GB and may take time to download

<i>The image is very large (1.3GB!) so it may take a little while to download and move.</i>

### 2. Configure API Keys
1. Navigate to the test directory:
```sh
cd test
```

2. Open `test_process_images.py` and add your API keys:

<img width="317" alt="Screenshot 2024-12-12 at 10 30 57 AM" src="https://github.com/user-attachments/assets/e1c03cc3-3948-4cba-bc3f-2d3a466ab27b" />

- **Replace YOUR_API_HERE with your Anthropic API KEY**
- **Replace YOUR_ROBOFLOW_API_HERE with your Roboflow API key**

[How to find your Roboflow API key](https://docs.roboflow.com/api-reference/authentication)
[How to find your Anthropic API key](https://docs.anthropic.com/en/api/getting-started)

### 3. Run the Test
```sh
python test_process_images.py
```

**This command will run ALL steps for ALL photos in the ```fullsize``` folder that have not yet been processed!**

## Calling Individual Steps

If you only want to run a single function at a time, you can use the following commands:

**Resize Drawers**

```sh 
python test_process_images.py resize_drawers
```

**Find Tray Coordinates**

Modify confidence or overlap % by changing 50 to any number 1-100. 50% is default.

```sh 
python test_process_images.py infer_drawers --drawer_confidence 50 --drawer_overlap 50
```

**Crop Trays from Drawers**

```sh 
python test_process_images.py crop_trays
```

**Resize Trays**

```sh 
python test_process_images.py resize_trays
```

**Find Label Coordinates**

UPDATE

**Find Specimen Coordinates**

Modify confidence or overlap % by changing 50 to any number 1-100. 50% is default.

```sh 
python test_process_images.py infer_trays --tray_confidence 50 --tray_overlap 50
```

**Crop Specimens from Trays**

```sh 
python test_process_images.py crop_specimens
```

**Find Specimen Outlines**

Modify confidence or overlap % by changing 50 to any number 1-100. 50% is default.

```sh 
python test_process_images.py infer_beetles --beetle_confidence 50 --beetle_overlap 50
```

**Create Binary Mask PNGs from Specimen Outlines**

```sh 
python test_process_images.py create_masks
```

**NEED UPDATES FOR OTHER STEPS HERE**

## Image and Data Outputs

<i>describe outputs here and ways to analyze data here </i>

# 4. Process New Images

## Decide Model Approach

### Public FMNH Roboflow Models

This will just involves putting the API key in and potentially changing version number. Nothing else needs to be changed.

### Create Your Own Roboflow Models

**WORKSPACE** 

Your workspace id can be found in your roboflow workspace page, under settings:

<img width="807" alt="Screenshot 2024-05-21 at 1 37 39 PM" src="https://github.com/EGPostema/DrawerDissect/assets/142446286/19016e31-2542-48b5-9e51-7372de3e5b90">

**MODEL / VERSION - REVISE WHEN MODEL IS PUBLIC**

To find your model's name and version in roboflow, go to your projects > choose your model > versions > click whatever version you want to use. You'll see something like this in the middle of the page:

<img width="782" alt="Screenshot 2024-05-20 at 1 39 37 PM" src="https://github.com/EGPostema/DrawerDissect/assets/142446286/e2918f19-9867-42d1-ae20-53369f2d4018">

In the script, for this model, I would input the information like this:

<img width="486" alt="Screenshot 2024-06-24 at 1 02 10 PM" src="https://github.com/EGPostema/DrawerDissect/assets/142446286/1070e844-ab02-4c6a-a605-bdf781498f62">

The model's name will always be uncapitalized and without spaces (or dashes instead of spaces). The version # will be to the right of the model name. This makes it easy to go back and just update the version # as you train better version of the same model! 

**CONFIDENCE / OVERLAP** 

You can personalize your desired % confidence and overlap for each model. The default is set to 50% for each - this  works well for most models, but can be changed by changing to 50 to any number between 0 and 100. 
- "50% confidence" means that only annotations the model is over 50% sure about will be recorded in the coordinates file.
- "50% overlap" means that the model expects that different objects in the JPG may have bounding boxes around them that overlap by up to 50%.

![Screenshot 2024-07-23 at 2 20 15 PM](https://github.com/user-attachments/assets/aa11408b-096c-4c0b-b21c-fe4652c832e9)

### DIY Models with Our Training Data

Describe suggestions for how to do this here - direct to google drive ??? where all my images/annotations are, organized by version

## Upload Your Images

Put all images in the ```fullsize``` folder. Ensure they are .jpgs, though the code could be modified to handle other file formats if needed. It is helpful to have a consistent naming convention for the drawers. For example, at the Field, we use a drawer name that is consistent with EMu, our museum databasing program. This name corresponds to the physical row, cabinet, and position that the drawer is located in (ex: "63_5_8" refers to a drawer in row 63, cabinet 5, 8 down from the top). Our photos are also timestamped. Any standard naming convention can be used, though dashes should generally be avoided ('_'s work better).

<img width="461" alt="Screenshot 2024-06-24 at 12 04 05 PM" src="https://github.com/EGPostema/DrawerDissect/assets/142446286/c6526924-908f-4999-af55-8c89962b2518">

As the processing script runs, it will use the names of your fullsize drawer images to organize all output files. So, for example, a tray image cropped from {drawerID_here}.jpg will then be named {drawerID_here}_tray_01.jpg and so on. The script also organizes images into folders and subfolders based on drawer and tray identities. Below is an example of how individual specimen photos are organized once they are cropped out.

<img width="262" alt="Screenshot 2024-07-23 at 2 08 42 PM" src="https://github.com/user-attachments/assets/06386a11-efee-445b-a007-8a36e654c0a1">

# 5. Transcribing Text from Tray and Specimen Labels

## For Test Image

## For New Images

# Use of AI Disclaimer




