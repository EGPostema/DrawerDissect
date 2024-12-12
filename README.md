# Introduction to DrawerDissect

**Welcome to DrawerDissect, an AI-powered method for processing whole drawers of insects!**

Using a combination of object detection, segmentation, and large-language models, this pipeline extracts individual-level photographs and data (taxonomic, geographic, phenotypic) from large, high-resolution images that contain many insect specimens. 

Normally, extracting this information takes an enormous amount of time and effort. With DrawerDissect, these outputs can be extracted (mostly) automatically.

<img width="1451" alt="Screenshot 2024-12-12 at 9 51 46 AM" src="https://github.com/user-attachments/assets/385ecb70-589a-4903-9027-ae876ca2decf" />

For more information on this project, [SEE THE FULL ARTICLE PRE-PRINT HERE](https://www.authorea.com/)

**To get started, follow the steps below:**
1. Set Up an Image-Processing Environment
2. Clone the Repository
3. Process Test Image
4. Process New Images
5. Transcribe Text from Tray and Specimen Labels

**TIP:** We highly recommend that you try the test image first, before moving on to your own whole-drawer images.

**Options for Models**
- [Public FMNH Roboflow Models](#public-fmnh-roboflow-models)
- [Create Your Own Roboflow Models](#create-your-own-roboflow-models)
- [DIY Models with Our Training Data](#diy-models-with-our-training-data)

# 1. Set Up an Image-Processing Environment

Create a python virtual environment (name can be anything, here we use 'drawerdissect'):

```sh 
python3 -m venv drawerdissect
```

Activate the virtual environment:

```sh
source drawerdissect/bin/activate
```

Install all required packages with pip:

```sh
pip install
pandas
numpy
Pillow
opencv-python
matplotlib
roboflow
anthropic
aiofiles
```

# 2. Clone the Repository

[First, make sure you have github installed.](https://github.com/git-guides/install-git)

Then, to clone this repository, use the following command:

```sh 
git clone https://github.com/EGPostema/DrawerDissect.git
```

Make sure to navigate to the correct project directory before you start adding and processing images:

```sh 
cd DrawerDissect
```

# 3. Process Test Image

## Download Test Image

instructions here

## Navigate to Test Folder

To try the script on an example FMNH drawer, first navigate to the test folder:

```sh 
cd est
```

## Add Roboflow Information

The test script is designed to work with [Roboflow](roboflow.com), a paid platform for training and deploying AI models. 
- To run the script as-is, **you will need a Roboflow account!**
- For alternatives, see [other model options here](#decide-model-approach)

For the test, you will need to have an **API KEY.** Your API key is **PRIVATE** to your own account.
- For help finding the roboflow API key for your account, [click here.](https://docs.roboflow.com/api-reference/authentication)

[SHOW IMAGE HERE]

To input your API in the script (shown above), find the test_process_images.py script. It can be edited using the ```nano``` command on both windows and mac, or via applications like notepad/textedit. Replace '___' with your API KEY.

## Running the Script

Once the script has been updated with information from roboflow, you can start the script within the ```DrawerDissect``` directory: 

```sh
python test_process_images.py
```

**This command will run ALL steps for ALL photos in the ```fullsize``` folder that have not yet been processed**

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




