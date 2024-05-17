# Introduction & Summary of Steps?

tbd

# Train Roboflow Models with Our Data

Provide link to most updated repository where we put our images and annotations

Describe how to upload and train the two models needed, using either the free or upgraded version of roboflow

Also describe how they can even update the model with their own data if they want (various ways to do this)

Make a note for the person to remember the model name, version, and their API key to use

# Set up a Conda Environment for COLORoptera Image Processing

Make sure that conda is installed and updated. Then, create a new conda environment that includes all the necessary packages for image resizing, cropping, and OCR.

```sh conda create -n <your-env-name> -c conda-forge python=3.9 pillow pandas pytesseract tesseract pip```

Activate your new environment.

```sh conda activate <your-env-name>```

Then, pip install roboflow so you can run inference. Roboflow can sometimes install weirdly, so it's good to specify exactly where you want it to go.

```sh /home/<your-username>/miniconda3/envs/<your-env-name>/bin/python -m pip install roboflow```

# Cloning the Repository

To clone this repository, use the following command:

```sh git clone https://github.com/EGPostema/coloroptera.git```

Make sure to navigate to the correct project directory before you start adding and processing images, which you can do with this command.

```sh cd coloroptera```

# Processing a Batch of New Images

describe where to put images here! ensure they are .jpgs, though the code could certainly be modified to handle other file formats if needed.


