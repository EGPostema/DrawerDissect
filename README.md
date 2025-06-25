# DrawerDissect :beetle: :scissors:

**DrawerDissect** is an AI-driven pipeline that automates the processing of whole-drawer images of insect specimens. It extracts individual specimen photos, measures specimen size, retrieves taxonomic information, and creates "masked" specimens for downstream analysis.

---

## 📖 Visual Overview

<img width="1000" alt="Screenshot 2025-02-06 at 11 08 53 AM" src="https://github.com/user-attachments/assets/5f27e287-e6c9-44eb-a2ad-cba05a4153b8" />

---

## 🚀 Quick Start Guide

### Prerequisites

- [Python](https://www.python.org/downloads/) (ver. 3+)
- [Git](https://git-scm.com/downloads)
- API keys from:
  - [Roboflow](roboflow.com) - for detecting and segmenting specimens
  - [Anthropic](anthropic.com) - for reading tray and specimen labels
- Supported image formats: TIF/TIFF, PNG, JPG/JPEG

DrawerDissect has been successfully used on:
- Our Windows computers (describe)
- My Mac (describe)
- Kelton's computer (describe)

---

### Installation

1. **Set Up Project in a Python Environment**

Unix systems (Mac, Linux)
```sh
git clone https://github.com/EGPostema/DrawerDissect.git
cd DrawerDissect
python -m venv dissectenv
source ./dissectenv/bin/activate
pip install -r requirements.txt
```

Windows
```sh
git clone https://github.com/EGPostema/DrawerDissect.git
cd DrawerDissect
python -m venv dissectenv
.\dissectenv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure API Keys**

Open `config.yaml` in the main directory, and add your API keys:

```yaml
api_keys:
  anthropic: "YOUR_ANTHROPIC_KEY" # replace YOUR_ANTHROPIC_KEY with your key
  roboflow: "YOUR_ROBOFLOW_KEY" # replace YOUR_ROBOFLOW_KEY with your key
```

- [Get Anthropic API Key](https://support.anthropic.com/en/articles/8114521-how-can-i-access-the-anthropic-api)
- [Get Roboflow API Key](https://docs.roboflow.com/api-reference/authentication)

❗This step is <ins>REQUIRED</ins> for the full pipeline to run.

Then, you can:
- [Process your own images](https://github.com/EGPostema/DrawerDissect/tree/main?tab=readme-ov-file#process-your-own-images)
- [OR try a test image first](https://github.com/EGPostema/DrawerDissect/tree/main?tab=readme-ov-file#try-a-test-image) (⭐ Recommended )

---

## 🧪 Run the Pipeline

### Process Your Own Images

1. Make sure you have installed DrawerDissect & set up the virtual environment
2. Place drawer images in `drawers/fullsize`
3. Check that `config.yaml` contains your API keys
4. Decide your model approach:

---

#### Option A: Use Public Field Museum Roboflow Models (⭐ DEFAULT, RECOMMENDED)

The script is set up to use FMNH models by default, defined in `config.yaml`

```yaml
# Example of how our models are configured

roboflow:
  workspace: "field-museum" # FMNH workspace default, can change to your own
  models:
    drawer:
      endpoint: "trayfinder-labels" # model name goes here
      version: 17 # can update versions as needed
      confidence: 50 # adjustable, set from 1-99 (higher # = greater threshold for model to return predictions)
      overlap: 50 # adjustable, set from 1-99 (higher # = higher expected overlap between bounding boxes)
```

**All Available FMNH Models (⭐ = default)**

   | Model Name            | Description   | Current Version   | mAP |
   | --------------------- | ------------- | ----------------- | --- |
   | trayfinder-base | detects trays in drawers  | 1 | 99.5% |
   | ⭐ trayfinder-labels  | detects trays (with tray labels) in drawers  | 17 | 99.5% |
   | ⭐ labelfinder  | detects tray label components  | 5 | 98.1% |
   | ⭐ bugfinder-kdn9e | detects specimens  | 13 | 99.0% |
   | ⭐ bugmasker-all | outlines specimen bodies (not taxon specific)  | 2 | 98.6% |
   | bugmasker-tigerbeetle | outlines specimen bodies (specailized)  | 13 | 98.2% |
   | bugmasker-pimeliinae | outlines specimen bodies (specialized)  | 4 | 98.5% |
   | ⭐ pinmasker | outlines specimen pins | 5 | 94.7% |

   Any of these models can be swapped in/out as long as workspace is set to `field-museum` [up-to-date 3/17/25]

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

Many **free, open-source** AI models exist for image processing and transcription. While we don’t currently support these architectures, users are welcome to modify our code to integrate open-source alternatives. Note that open source models may have specific hardware/software requirements for GPU support.

**Possible Free Alternatives**

   | Model Function | Possible Alternatives | Model it Could Replace |
   | ---------- | --- | ---------- |
   | Detection | YOLOv8, Detectron2, mmdetection, TensorFlow Object Detection, OpenCV DNN Module | ROBOFLOW: trayfinder, labelfinder, bugfinder |
   | Segmentation | YOLOv8-seg, Detectron2, DeepLabV3+, SAM (Segment Anything Model), OpenCV GrabCut | ROBOFLOW: bugmasker, pinmasker |
   | Tray Label Transcription | LLaVa, TrOCR (Transformer OCR), Tesseract OCR, EasyOCR | ANTHROPIC |
   | Collection Location Reconstruction | LLaVa | ANTHROPIC |


**We provide all FMNH model training data - feel free to use these to train your own open source models!**
- Access the data here: ❗ [COMING SOON]
- Data structure details: ❗ [COMING SOON]

---

5. Configure the pipeline

Standard FMNH drawers contain **unit trays** with labels (see below)

<img width="800" alt="Screenshot 2024-12-16 at 3 44 59 PM" src="https://github.com/user-attachments/assets/387e6413-375f-401a-a258-ffb46f6286e4" />

By default, DrawerDissect crops and transcribes:
  - **barcodes**
  - **taxonomic IDs**

DrawerDissect also has the option to:
  - **transcribe visible specimen labels**
  - **estimate collection location from that text**

**For different drawer setups / desired outputs, simply adjust `config.yaml`:**

```yaml
processing:
  transcribe_barcodes: true  # Set to false if no barcodes
  transcribe_taxonomy: true  # Set to false if no taxonomic IDs
  transcribe_specimen_labels: true  # Set to false to skip specimen label transcription/estimation
```
6. Run the Script

  ```bash
  # this command runs all steps in the pipeline
  python process_images.py all
  ```

[How to run individual steps](https://github.com/EGPostema/DrawerDissect/blob/main/README.md#calling-individual-steps)

---
### Try a Test Image
1. [Download the test image](https://drive.google.com/drive/folders/1NHV9MSR-sjmAW43KlyPfSB9Xr5ZTvJFt?usp=drive_link) (large image, be patient!)
2. Make sure you have installed DrawerDissect & set up the virtual environment
3. Place it in `drawers/fullsize`
4. Check that `config.yaml` contains your API keys
5. Edit `config.yaml` to enable metadata processing
6. Run the Script

  ```bash
  # this command runs all steps in the pipeline
  python process_images.py all
  ```

See example outputs below!

---

## 📊 Example Outputs

📷 **Individual Tray Images** `drawers/trays`

<img width="666" alt="Screenshot 2025-01-14 at 4 22 16 PM" src="https://github.com/user-attachments/assets/8bb72f93-bea3-4eaf-b28f-2caa7ee06ce1" />

🗺️ **Specimen Location Guides** `drawers/guides`

![image](https://github.com/user-attachments/assets/c2d29085-a1f3-4745-814b-9bcc85697a23)

📷 **Individual Specimen Images** `drawers/specimens`

<img width="678" alt="Screenshot 2025-01-14 at 4 37 46 PM" src="https://github.com/user-attachments/assets/937673ef-f733-468b-b016-7b8b87998ec3" />

📏 **Measurements + Example Size Visualizations** `drawers/measurements`

<img width="660" alt="Screenshot 2025-01-21 at 3 19 56 PM" src="https://github.com/user-attachments/assets/f3c354d3-8fd6-4990-9f3f-c4d8197d0380" />

🏁 **Binary Masks** `drawers/masks/full_masks`

<img width="670" alt="Screenshot 2025-01-15 at 8 49 05 PM" src="https://github.com/user-attachments/assets/0752cad1-a299-4dff-9e8c-5e19fcff20cb" />

📷 **Fully Masked Specimens** `drawers/transparencies` & `drawers/whitebg_specimens`

<img width="670" alt="Screenshot 2025-01-15 at 10 02 32 AM" src="https://github.com/user-attachments/assets/cdf044a5-e1e2-4cc7-beef-c113cd5cc276" />

📝 **Data in Timestamped Folders** `drawers/data`

![data](https://github.com/user-attachments/assets/219db5f4-e612-49f4-8283-4cf0957d49a8)

Contains:
  - seperate CSVs,
  - a merged data CSV,
  - and a summary of drawer-level data.
    
---

## 🔧 Advanced Options

### Calling Individual Steps

You can run specific steps of the pipeline individually:

```bash
python process_images.py resize_drawers
```

Or in unique combinations:

```bash
python process_images.py resize_drawers find_trays crop_trays
```

To run a step and all steps after, use `--from`

```bash
python process_images.py --from create_masks
```

To run all steps up to a specific step, use `--until`

```bash
python process_images.py --until create_transparency
```

Finally, `--from` and `--until` can be combined to run sets of steps in order:

```bash
# runs all steps between create_masks and create_transparency
python process_images.py --from create_masks --until create_transparency

# runs resize_trays and then find_specimens through to validate_speclabels
python process_images.py resize_trays --from find_specimens --until validate_speclabels

# runs resize_trays, then find_specimens and all steps after
python process_images.py resize_trays --from find_specimens
```

### Steps Available:

```sh
all # to run all steps, in the order below
resize_drawers
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

If you have a set of **individual specimen photos** you want masked, measured, and turned into backgroundless images:

1. Create folder `drawers/specimens`
2. Add all specimen images to `drawers/specimens`
3. Configure `config.yaml` with API keys
4. Run the command:
   
```sh
python process_images.py --from outline_specimens --until create_transparency
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

#### Example 3: Processing Drawers With NO Trays

1. Create folder `drawers/trays`
2. Add drawers to `drawers/trays` instead of `drawers/fullsize`
3. Configure `config.yaml` with API keys
4. Edit config.yaml as follows:

```yaml
processing:
  process_metadata: false  # Set to false
  transcribe_barcodes: false  # Set to false
  transcribe_taxonomy: false  # Set to false
```

5. Run the command:

```sh
python process_images.py resize_trays --from find_specimens --until validate_speclabels
```

### Tuning LLM Prompts

We use a large language model, Claude Sonnet 3.5, to transcribe text from images. The prompts fed to Claude can be edited in `config.yaml`:

```yaml
prompts:
  barcode: # prompt for transcribing barcodes
    system: |
      You are a barcode reading tool. You should output only the number 
      (or letter-number string) found in the image. If no valid barcode 
      is found, output 'none'.
    user: |
      Read the barcode number. Output only the number, no explanations.
  
  taxonomy: # prompt for transcribing and organizing taxonomic IDs
    system: |
      You are a taxonomic label transcription tool specializing in natural 
      history specimens. Your task is to:
      1. Provide a complete transcription of the entire label
      2. Extract the taxonomic name, including any genus, subgenus, species, 
         and subspecies information
      3. Extract the taxonomic authority (author and year)

      For missing elements, output 'none'. Format your response as a structured 
      dictionary with these three keys:
      {
        'full_transcription': 'complete text as shown',
        'taxonomy': 'only taxonomic name (Genus (Subgenus) species subspecies)', 
        'authority': 'author, year'
      }
    user: |
      Transcribe this taxonomic label, preserving the exact text and extracting 
      the taxonomic name and authority. Output only the dictionary, no explanations.
  
  specimen_label: # prompt for transcribing any visible text, verbatim, from specimen labels
    system: |
      You are a natural history specimen label transcription tool specializing in precise, verbatim transcription. Your task is to:
          1. Transcribe ALL visible text exactly as it appears, including:
             - Punctuation, abbreviations, and special characters
             - Unclear or partially visible text
             - Handwritten text
          2. Preserve the exact spelling and formatting, even if it appears incorrect
          3. Do not interpret, correct, or standardize any text
          4. Do not skip any text, even if it seems unimportant
          5. Most text will be horizontal, read left-to-right. Occasionally, text may be vertical or upside-down.
    user: |
      Transcribe any visible text. Output 'no text found' if none visible. 
      Transcribe text verbatim. No explanations, descriptions, or commentary.
  
  location: # prompt for estimating locations from verbatim text
    system: |
      You are a geographic data extractor specialized in natural history specimen labels. 
      Your task is to:
      1. Look for geographic information only, considering:
         - Country, state/province, county, city, specific locality
      2. IGNORE non-geographic elements:
         - Collection metadata (Det., Coll., FMNH, Field Museum, Museum)
         - Taxonomic information
         - Dates and collector names
      3. For geographic inference:
         - Only infer larger regions when unambiguous (e.g., "Paris, France" -> "France")
         - Do not infer if multiple possibilities exist (e.g., "Springfield" could be many states)
         - Include only explicitly stated or unambiguously implied locations
      4. Handle special cases:
         - Historical place names: use historical name, add modern name in brackets
    user: |
      Extract geographic location from this text: {text}. Format: largest to 
      smallest unit, comma-separated. Output 'no location found' if none present. 
      No explanations or notes.
  
  validation: # prompt for comparing/validating estimated locations to the verbatim text
    system: |
      You are a geographic data validator specializing in museum specimen labels. 
      Your task is to:
      1. Examine the transcribed text and interpreted location to evaluate whether they are a strong match
      2. Make a final location determination considering:
         - The verbatim transcribed text
         - The proposed location
         - Standard geographic abbreviations in specimen labels (e.g., USA: MT = USA, Montana)
         - Some partial information is still valid (e.g., a clear state/province even without city/county)
         - Conventional collection abbreviations, e.g. Det. / Col. are typically not locations
         - Locations derived from 'Field Museum' or 'FMNH' or 'Chicago Field Museum' 
           are not valid, as this is where many specimens are housed
         - Avoid specific directional information as this easy to misinterpret
           
      3. Respond with a dictionary containing these fields:
        {
          'verbatim_text': The raw text exactly as transcribed from the original image,
          'proposed_location': The location string being validated,
          'validation_status': Must be one of these exact values:
              'VERIFIED' - Use when:
                  - Text contains clear geographic identifiers (e.g., standard country/state codes like "USA: MT")
                  - Location matches established abbreviation conventions
                  - Partial location information is okay if unambiguous (e.g., clear state without county)
              'UNRELIABLE' - Use when:
                  - Geographic terms are ambiguous or could be non-geographic
                  - Location interpretation goes beyond what's supported by the text
                  - Proposed location misinterprets collection abbreviations (e.g., reading 'Det.' as Detroit)
              'UNKNOWN' - Use when no clear location information is found in the text,
          'final_location': Must be either:
              - A standardized location string from largest to smallest unit (e.g., "USA, Montana")
                which can be:
                * A new determination if the proposed location was incorrect
                * An expansion of a previous valid determination with newly validated details
                * A more conservative version of the proposed location if only part can be verified
                (only if status is VERIFIED)
              - 'UNKNOWN' (for UNRELIABLE or UNKNOWN status),
          'confidence_notes': Concise sentence explaining the validation decision, specifically noting
              any abbreviation interpretations, historical names, uncertainty factors, or potential for future expansion
              with additional evidence
        }
    user: |
      Validate this location data:
      Transcribed text: {transcribed_text}
      Proposed location: {proposed_location}
  ```

In general, we recommend editing the **system** prompt (which is more descriptive) rather than the **user** prompt. 
  - Any text within {curved brackets} are **defined objects** needed for the script
  - Be sure to maintain standard tab formatting so that prompts are in the correct section!

---

## 📋 Troubleshooting

❗ **Script not working? Check that you have...**
  - [x] Cloned or downloaded the repository
  - [x] Navigated to the correct directory, either `DrawerDissect` or `DrawerDissect-main`
  - [x] Created and activated a virtual environment with the required packages
  - [x] Decided on a model approach 
  - [x] Edited (and saved) `config.yaml` accordingly

❗ More troubleshooting/tips to come...
