# Set up a Conda Environment for COLORoptera

Make sure that conda is installed and updated. Then, create a new conda environment that includes all the necessary packages.

```conda create -n <your-env-name> -c conda-forge python=3.9 pillow pandas pytesseract tesseract pip```

Then, pip install roboflow. Roboflow can sometimes install weirdly, so it's good to specify exactly where you want it to go.

```/home/<your-username>/miniconda3/envs/<your-env-name>/bin/python -m pip install roboflow```


