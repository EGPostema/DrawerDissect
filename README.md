# Introduction 

Welcome to __, and AI-powered method for processing whole-drawer images of insects into individual specimens. More summary stuff here...

1. bla
2. bla
3. bla
4. bla

Expected input --> expected outputs

# 1. Train Roboflow Models with Our Data

Provide link to most updated repository where we put our images and annotations

Describe how to upload and train the two models needed, using either the free or upgraded version of roboflow

Also describe how they can even update the model with their own data if they want (various ways to do this)

**Make a note for the person to remember the model name, version, and their API key to put in the master image-processing script! Other than uploading images to /drawers/fullsize, this should be the only thing necessary to directly modify**

# 2. Set up a Conda Environment for COLORoptera Image Processing

Make sure that conda is installed and updated. Then, create a new conda environment that includes all the necessary packages for image resizing, cropping, and OCR. Make sure to replace ```<your-env-name>``` with the actual name you want for the environment.

```sh 
conda create -n <your-env-name> -c conda-forge python=3.9 pillow pandas pytesseract tesseract pip
```

Activate your new environment.

```sh 
conda activate <your-env-name>
```

Then, pip install roboflow so you can run inference. Roboflow can sometimes install weirdly, so it's good to specify exactly where you want it to go. Make sure to replace ```<your-username>``` with your real username, or the appropriate path to ~/bin/python

```sh
/home/<your-username>/miniconda3/envs/<your-env-name>/bin/python -m pip install roboflow
```

You can double-check that everything is installed properly with the following commands:

```sh
pip list | grep roboflow
conda list pillow
conda list pandas
conda list pytesseract
conda list tesseract
```

It's also useful to make sure roboflow is in the right place:
```sh
ls /home/<your-username>/miniconda3/envs/<your-env-name>/lib/python3.9/site-packages/roboflow
```


# 3. Cloning the Repository

To clone this repository, use the following command:

```sh 
git clone https://github.com/EGPostema/coloroptera.git
```

Make sure to navigate to the correct project directory before you start adding and processing images, using ```cd```.

```sh 
cd coloroptera
```

You can use the ```cd``` and ```ls``` commands to navigate through the directory and see what folders and files are present. You can also use ```pwd``` to check your current directory, which should be ~/coloroptera. 

Make sure that you have all of the following within the main project folder:

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
└── process_images.py  <-- This is the master script that runs all the individual processes from 'functions'
```

# 4. Processing a Batch of New Images

Put everything in the 'drawers' folder! ensure they are .jpgs, though the code could certainly be modified to handle other file formats if needed.

Make sure that process_images.py is modified for the user's roboflow details (API key, model names, versions, and desired confidence/overlap).

How to find roboflow API key: https://docs.roboflow.com/api-reference/authentication

Finding your model's name and version, go to your projects > choose your model > versions > click whatever version you want to use. You'll see something like this in the middle of the page:

<img width="622" alt="Screenshot 2024-05-20 at 1 35 34 PM" src="https://github.com/EGPostema/coloroptera/assets/142446286/0147fdd6-699d-49e1-8fc8-6a30fed14ef3">

The model's name will always be uncapitalized and without spaces. The version # will be to the right of the model name. This makes it easy to go back and just update the version # as you train better models!

Once the script has been updated with information from roboflow, you can start the script within the ```coloroptera``` directory with command ```python process_image.py```


