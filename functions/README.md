# Summary of Image Processing Scripts

The "functions" folder contains 7 scripts that resize images, generate coordinates via roboflow, transcribe label information (if applicable), and crop images. Here is a step-by-step of each process, with inputs and outputs:

## resize_drawer.py

**Summary**
- Resizes full-size drawer images to 1000 pixels wide.

**Process**
- Iterate Through Folder: Processes each full-size drawer image.
- File Handling: Ensures only .jpg images are processed.
- Skip Existing Resized Images: Skips processing if the resized image already exists.
- Resize Image: Resizes the image to a width of 1000 pixels, maintaining aspect ratio.
- Save Resized Image: Saves the resized image to the 'resized' folder with _1000.jpg suffix.

**Inputs**
- Full-size drawer images from fullsize_dir.

**Outputs**
- Resized drawer images saved in resized_dir.

---

## infer_drawers.py

**Summary**
- Detects trays in resized drawer images and saves bounding boxes.

**Process**
- **Directory Setup**: Ensures the output directory exists.
- **Roboflow Initialization**: Initializes Roboflow with the provided API key and model details.
- **Iterate Through Input Directory**: Processes each resized drawer image.
  - **File Handling**: Ensures only `_1000.jpg` images are processed.
  - **Check for Existing JSON**: Skips processing if a JSON file already exists for an image.
  - **Run Inference**: Uses the Roboflow model to predict bounding boxes for trays within the image.
  - **Save JSON Output**: Saves the prediction results (bounding boxes) as a JSON file in the ~/resized/coordinates folder.

**Inputs**
- Resized drawer images from `resized_dir`.
- Roboflow details from `process_images.py`.

**Outputs**
- JSON files containing tray bounding boxes saved in `coordinates_dir`.

---

## crop_trays.py

**Summary**
- Crops trays from full-size drawer images bbox coordinates scaled up from the resized drawers.

**Process**
- **Initialize Timer**: Records the start time for processing.
- **Define Directory**: Sets up the directory containing coordinates of resized trays.
- **Iterate Through Resized Images**: Processes each resized drawer image.
  - **File Handling**: Ensures only `_1000.jpg` images are processed.
  - **Path Setup**: Determines paths for original and resized images and corresponding JSON files.
  - **JSON Existence Check**: Skips processing if the JSON file for an image is missing.
  - **Load JSON Data**: Reads the JSON file to get annotations (bounding boxes).
  - **Calculate Scale Factors**: Determines scaling between original and resized images.
  - **Crop Images**: Uses annotations to crop the original image and saves the cropped trays with formatted names.
- **End Timer**: Calculates and prints the total processing time.

**Inputs**
- Full-size drawer images from `fullsize_dir`.
- Resized drawer images from `resized_dir`.
- JSON files with annotations from `coordinates_dir`.

**Outputs**
- Cropped tray images saved in `trays_dir`.

---

## resize_trays.py

**Summary**
- Resizes cropped tray images to 1000 pixels wide.

**Process**
- **Iterate Through Input Directory**: Processes each cropped tray image.
  - **File Handling**: Ensures only `.jpg` images are processed.
  - **Skip Existing Resized Images**: Skips processing if the resized image already exists.
  - **Resize Image**: Resizes the image to a specified width (default 1000 pixels), maintaining aspect ratio.
  - **Save Resized Image**: Saves the resized image to the output directory with `_1000.jpg` suffix.

**Inputs**
- Cropped tray images from `trays_dir`.

**Outputs**
- Resized tray images saved in `resized_trays_dir`.

---

## label_transcription.py

**Summary**
- Transcribes labels from resized tray images and saves those data to a CSV with multiple columns.

**Process**
- **Define Directory and Paths**: Sets up the directory for saving label data and the CSV file path.
- **Check Existing Files**: Reads the existing CSV file to avoid reprocessing already transcribed images.
- **Iterate Through Resized Trays**: Processes each resized tray image.
  - **File Handling**: Ensures only `.jpg` images are processed and skips checkpoints.
  - **Extract Label Info**: 
    - **Crop Image**: Crops the top part of the image where the label is expected.
    - **OCR Processing**: Uses Tesseract to extract text from the cropped label image.
    - **Parse Text**: Extracts taxonomic information, geographical code, and year from the text.
    - **Handle Failures**: Skips images if OCR fails to extract meaningful text.
  - **Extract ID**: Crops the top-left region of the image to extract an ID number using OCR.
  - **Store Data**: Appends the extracted data to the list.
- **Save to CSV**: Writes the data to the CSV file, appending if the file already exists.

**Inputs**
- Resized tray images from `resized_trays_dir`.

**Outputs**
- CSV file containing transcribed label info saved in the `label_data` directory.

---

## infer_trays.py

**Summary**
- Detects specimens in resized tray images and saves bounding boxes.

**Process**
- **Directory Setup**: Ensures the output directory exists.
- **Roboflow Initialization**: Initializes Roboflow with the provided API key and model details.
- **Iterate Through Input Directory**: Processes each resized tray image.
  - **File Handling**: Ensures only `_1000.jpg` images are processed.
  - **Check for Existing JSON**: Skips processing if a JSON file already exists for an image.
  - **Run Inference**: Uses the Roboflow model to predict bounding boxes for specimens within the image.
  - **Save JSON Output**: Saves the prediction results (bounding boxes) as a JSON file in ~/resized_trays/coordinates.

**Inputs**
- Resized tray images from `resized_trays_dir`.
- Roboflow details from `process_images.py`.

**Outputs**
- JSON files containing specimen bounding boxes saved in `resized_trays_coordinates_dir`.

---

## crop_specimens.py

**Summary**
- Crops specimens from trays using bounding boxes, scaling between fullsize/resized images, and adding a small buffer around each crop.

**Process**
- **Initialize Timer**: Records the start time for processing.
- **Define Directory**: Sets up the directory containing coordinates of resized trays.
- **Iterate Through Resized Images**: Processes each resized tray image.
  - **File Handling**: Ensures only `_1000.jpg` images are processed.
  - **Path Setup**: Determines paths for original and resized images and corresponding JSON files.
  - **JSON Existence Check**: Skips processing if the JSON file for an image is missing.
  - **Load JSON Data**: Reads the JSON file to get annotations (bounding boxes).
  - **Calculate Scale Factors**: Determines scaling between original and resized images.
  - **Crop Images**: Uses annotations to crop the original image with a 50-pixel buffer and saves the cropped specimens with formatted names.
- **End Timer**: Calculates and prints the total processing time.

**Inputs**
- Cropped tray images from `trays_dir`.
- Resized tray images from `resized_trays_dir`.
- JSON files with annotations from `resized_trays_coordinates_dir`.

**Outputs**
- Cropped specimen images saved in `specimens_dir`.
