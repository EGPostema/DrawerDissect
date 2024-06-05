# Introduction - WIP

**Welcome to COLORoptera, and AI-powered method for processing whole-drawer images of insects!**

<i>(Add a short summary here about intended purposes etc. Python + conda environment + OS command line. Meant to be quite simple / for a beginner at computer programming.)</i>

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

<i>Also describe how they can even update the model with their own data if they want (various ways to do this)</i>

# 2. Set up a Conda Environment

Make sure that conda is installed and updated. Then, create a new conda environment that includes all the necessary packages for image resizing, cropping, and OCR. Make sure to replace ```<your-env-name>``` with the actual name you want for the environment. 
- On a Mac, you can do this in the terminal.
- For Windows, search for and open the "Anaconda Prompt" to create your conda environment.

```sh 
conda create -n <your-env-name> -c conda-forge python=3.9 pillow pandas pytesseract tesseract pip git
```

Activate your new environment.

```sh 
conda activate <your-env-name>
```

Then, pip install roboflow so you can run inference. Roboflow can sometimes install weirdly, so it's good to specify exactly where you want it to go. Make sure to input your real username and environment name and ensure that the path looks correct. 

<b>For Mac</b>
```sh
/home/<your-username>/miniconda3/envs/<your-env-name>/bin/python -m pip install roboflow
```

<b>For Windows</b>
```sh
C:\Users\<your-username>\AppData\Local\miniconda3\envs\<your-env-name>\python.exe -m pip install roboflow
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

It's also useful to make sure roboflow is in the right place:
```sh
ls /home/<your-username>/miniconda3/envs/<your-env-name>/lib/python3.9/site-packages/roboflow
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

You can use the ```cd``` and ```ls``` commands to navigate through the directory and see what folders and files are present. You can also use ```pwd``` to check your current directory, which should be ```coloroptera``` 

**Before you start processing new images,** make sure that you have all of the following within the main project folder:

```
coloroptera/
├── functions/ <-- This is where all the image processing scripts live!
│ ├── resize_drawer.py 
│ ├── infer_drawers.py
│ ├── crop_trays.py
│ ├── resize_trays.py
│ ├── label_transcription.py
│ ├── infer_trays.py
│ └── crop_specimens.py
├── drawers/
│ ├── fullsize/  <-- This is where you will add new images to process
└── process_images.py  <-- This is the master script that runs all the processing steps
```

# 4. Process a Batch of New Images

## Upload Images

Put all images in ~/drawers/fullsize. Ensure they are .jpgs, though the code could probably be modified to handle other file formats if needed. It is helpful to have a consistent naming convention for the drawers that is also taxonomically descriptive (if applicable).

<i>PHOTO HERE!</i>

## Add Your Roboflow Info

Make sure that process_images.py is modified for your own roboflow details. You will need to find the following information: 
- API key
- Workspace id
- Model names and versions
- Desired model confidence/overlap.

<img width="1038" alt="Screenshot 2024-05-21 at 1 56 55 PM" src="https://github.com/EGPostema/coloroptera/assets/142446286/864a9d8a-a6a3-4d59-8d78-3887125578b1">

The easiest way to modify these details in is to edit the script directly with the command ```nano process_images.py```

### API KEY 

Your API key is PRIVATE to your own account. Make sure not to share this widely. Here's how to find roboflow API key: https://docs.roboflow.com/api-reference/authentication

### WORKSPACE 

Your workspace id can be found in your roboflow workspace page, under settings:

<img width="807" alt="Screenshot 2024-05-21 at 1 37 39 PM" src="https://github.com/EGPostema/coloroptera/assets/142446286/19016e31-2542-48b5-9e51-7372de3e5b90">

### MODEL / VERSION

To find your model's name and version in roboflow, go to your projects > choose your model > versions > click whatever version you want to use. You'll see something like this in the middle of the page:

<img width="782" alt="Screenshot 2024-05-20 at 1 39 37 PM" src="https://github.com/EGPostema/coloroptera/assets/142446286/e2918f19-9867-42d1-ae20-53369f2d4018">

The model's name will always be uncapitalized and without spaces (or dashes instead of spaces). The version # will be to the right of the model name. This makes it easy to go back and just update the version # as you train better version of the same model! 

**Make sure to fill in both MODEL_ENDPOINT and VERSION for EACH model used in this script.** 
- One model should seperate trays from drawers ('TRAY_SEPERATING_MODEL_HERE')
- The other should seperate specimens from trays ('SPECIMEN_SEPERATING_MODEL_HERE')

### CONFIDENCE / OVERLAP 

You can personalize your desired % confidence and overlap for each model. The default is set to 50% for each. Numbers can be changes to anything from 1-100.
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
python process_images.py transcribe_labels
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
