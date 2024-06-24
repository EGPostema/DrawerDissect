# Introduction - WIP

**Welcome to COLORoptera, and AI-powered method for processing whole-drawer images of insects!**

<i>(Add a short summary here about intended purposes etc. Python + conda environment. Meant to be quite simple / for someone with VERY basic knowledge of command-line functions.</i>

**To get started, follow the steps below:**
1. Train Roboflow Models 
2. Set up a Conda Environment
3. Clone the Repository
4. Process a Batch of New Images

For a full summary of each processing step (with descriptions of inputs and outputs), [see the README file in the 'functions' folder](https://github.com/EGPostema/coloroptera/blob/main/functions/README.md)

# 1. Train Roboflow Models - WIP

## Quick-Start: Use Our Data to Train Basic Models

<i> - Provide link to most updated repository where we put our images and annotations</i>

<i> - Describe how to upload and train the two models needed, using either the free or upgraded version of roboflow</i>

## Update Models with your Own Data

<i>Also describe how they can even update the model with their own data if they want, or train models for totally new functions</i>

# 2. Set up a Conda Environment

Make sure that miniconda is installed and updated. [Download the latest version here.](https://docs.anaconda.com/free/miniconda/)

Then, create a new conda environment that includes all the necessary packages for image resizing, cropping, and OCR. 

- On a Mac, you can do this in the terminal.
- For Windows, search for and open the "Anaconda Prompt" to create your conda environment.

To create the environment, use the command below. Make sure to replace ```<your-env-name>``` with the actual name you want for the environment.

```sh 
conda create -n <your-env-name> -c conda-forge python=3.9 pillow pandas pytesseract tesseract pip git
```

Activate your new environment.

```sh 
conda activate <your-env-name>
```

Then, pip install roboflow.

```sh
pip install roboflow
```

You can double-check that everything is installed properly with the following commands:

```sh
pip list | grep roboflow
conda list pillow
conda list pandas
conda list pytesseract
conda list tesseract
conda list git
```

# 3. Clone the Repository

To clone this repository, use the following command:

```sh 
git clone https://github.com/EGPostema/coloroptera.git
```

Make sure to navigate to the correct project directory before you start adding and processing images:

```sh 
cd coloroptera
```

You can use the ```cd``` and ```ls``` commands to navigate through the directory and see what folders and files are present.

**Before you start processing new images,** make sure that you have all of the following folders/files:

<img width="299" alt="Screenshot 2024-06-18 at 12 21 05 PM" src="https://github.com/EGPostema/coloroptera/assets/142446286/36ca24fb-6505-4b9e-a399-7e9cc68f8cd1">

Within the ```functions``` folder, there should be 7 scripts for the 7 different image processing steps (2 for cropping, 2 for running inference, 1 for label transcription, and 2 for image resizing):

- crop_specimens.py
- crop_trays.py
- infer_drawers.py
- infer_trays.py
- label_transcription.py
- resize_drawer.py
- resize_trays.py

Each of these steps gets called on automatically by the main processing script in step 4.

# 4. Process a Batch of New Images

## Upload Images

Put all images in the ```fullsize``` folder. Ensure they are .jpgs, though the code could  be modified to handle other file formats if needed. It is helpful to have a consistent naming convention for the drawers. For example, at the Field, we use a drawer name that is consistent with EMu, our museum databasing program. This name corresponds to the physical row, cabinet, and position that the drawer is located in (ex: "63_5_8" refers to a drawer in row 63, cabinet 5, 8 down from the top). Our photos are also timestamped.

<img width="461" alt="Screenshot 2024-06-24 at 12 04 05 PM" src="https://github.com/EGPostema/coloroptera/assets/142446286/c6526924-908f-4999-af55-8c89962b2518">

**This script is currently only set up to handle filenames with the ```##_##_##_timestamp.jpg``` naming convention, though we plan to update this in future versions.**

## Add Your Roboflow Info

Make sure that process_images.py is modified for your own roboflow details. **The script WILL NOT RUN otherwise.** 

You will need to find the following information: 
- API key
- Workspace id
- Model names and versions
- Desired model confidence/overlap

![Screenshot 2024-06-24 at 12 55 05 PM](https://github.com/EGPostema/coloroptera/assets/142446286/a2181fad-c177-41bc-9ea7-7d46dd75db78)

process_image.py can be edited using the ```nano``` command on both windows and mac, or via applications like notepad and textedit.

### API KEY 

Your API key is PRIVATE to your own account. Make sure not to share this widely. Here's how to find the roboflow API key for your account: https://docs.roboflow.com/api-reference/authentication

### WORKSPACE 

Your workspace id can be found in your roboflow workspace page, under settings:

<img width="807" alt="Screenshot 2024-05-21 at 1 37 39 PM" src="https://github.com/EGPostema/coloroptera/assets/142446286/19016e31-2542-48b5-9e51-7372de3e5b90">

### MODEL / VERSION

To find your model's name and version in roboflow, go to your projects > choose your model > versions > click whatever version you want to use. You'll see something like this in the middle of the page:

<img width="782" alt="Screenshot 2024-05-20 at 1 39 37 PM" src="https://github.com/EGPostema/coloroptera/assets/142446286/e2918f19-9867-42d1-ae20-53369f2d4018">

The model's name will always be uncapitalized and without spaces (or dashes instead of spaces). The version # will be to the right of the model name. This makes it easy to go back and just update the version # as you train better version of the same model! 

**Make sure to fill in both MODEL NAME and VERSION for EACH model used in this script.** 
- One model should seperate trays from drawers ('DRAWER_MODEL_ENDPOINT')
- One should seperate specimens from trays ('TRAY_MODEL_ENDPOINT')
- The third should find the location of label information ('LABEL_MODEL_ENDPOINT')

### CONFIDENCE / OVERLAP 

You can personalize your desired % confidence and overlap for each model. The default is set to 50% for each - this  works well for most models. 
- "50% confidence" means that only annotations the model is over 50% sure about will be recorded in the coordinates file.
- "50% overlap" means that the model expects that different objects in the JPG may have bounding boxes around them that overlap by up to 50%.

<img width="1031" alt="Screenshot 2024-05-21 at 1 55 19 PM" src="https://github.com/EGPostema/coloroptera/assets/142446286/161ff11d-e05e-428c-b168-e1e306869527">

## Running the Script

Once the script has been updated with information from roboflow, you can start the script within the ```coloroptera``` directory: 

```sh
python process_images.py
```

## Calling Individual Steps

If you only want to run a single function, you can use the following commands:

**Resize Drawers**

```sh 
python process_images.py resize_drawers
```

**Find Tray Coordinates**

Modify confidence or overlap % by changing 50 to any number 1-100. 50% is default.

```sh 
python process_images.py infer_drawers --drawer_confidence 50 --drawer_overlap 50
```

**Crop Trays from Drawers**

```sh 
python process_images.py crop_trays
```

**Resize Trays**

```sh 
python process_images.py resize_trays
```

**Transcribe Labels**

```sh 
python process_images.py transcribe_labels --label_confidence 30 --drawer_overlap 50
```

**Find Specimen Coordinates**

Modify confidence or overlap % by changing 50 to any number 1-100. 50% is default.

```sh 
python process_images.py infer_trays --tray_confidence 50 --tray_overlap 50
```

**Crop Specimens from Trays**

```sh 
python process_images.py crop_specimens
```

## Outputs and Analysis - WIP

<i>describe outputs here and ways to analyze data here </i>
