# <img src="https://github.com/user-attachments/assets/26e883f0-f643-4715-80d6-abb2225bdb75" width="75" height="75">rawerDissect

**DrawerDissect** is an AI-driven pipeline for processing whole-drawer images of insect specimens. It can crop out specimen photos, measure specimens, transcribe text, and create "masked" specimens for phenotypic analysis.

---

![smalldemo](https://github.com/user-attachments/assets/46c1ce5d-7281-401e-b763-0ec498b1bc0a)

---

## Prerequisites

- [Python](https://www.python.org/downloads/) (ver. 3+)
- [Git](https://git-scm.com/downloads)
- An [Anthropic API key](https://support.anthropic.com/en/articles/8114521-how-can-i-access-the-anthropic-api) for reading tray and specimen labels
- A [Roboflow API key](https://docs.roboflow.com/api-reference/authentication) (only needed for Roboflow cloud deployment -- see [Deployment Options](#deployment-options))
- Supported image formats: TIF/TIFF, PNG, JPG/JPEG

DrawerDissect has run successfully on the following systems:

| System | OS | CPU | RAM | GPU |
|--------|----|----|-----|-----|
| MacBook Pro | macOS | 2.3 GHz Dual-Core Intel Core i5 | 8 GB | Intel Iris Plus Graphics 640 1536 MB |
| Mac mini | macOS | Apple M2 (8-core) | 16 GB | M2 Integrated (10-core) |
| Windows | Windows 11 | AMD Ryzen 7 7800X3D | 32 GB | NVIDIA GeForce RTX 4060 |
| Windows | Windows 11 | Intel i5-13400F | 32 GB | NVIDIA GeForce RTX 4060 |

Current Version: v0.2.0

---

## Citation

Postema, E.G., Briscoe, L., Harder, C., Hancock, G.R.A., Guarnieri, L.D, Eisel, T., Welch, K., Fisher, N., Johnson, C., Souza, D., Sepulveda, T., Phillip, D., Baquiran, R., de Medeiros, B.A.S. 2025. **DrawerDissect: Whole-drawer insect imaging, segmentation, and trait extraction using AI.** <i>EcoEvoRxiv (pre-print)</i>. https://doi.org/10.32942/X2QW84

---

## Installation

**1. Clone the repository and set up a Python environment**

Unix systems (Mac, Linux)
```sh
git clone https://github.com/EGPostema/DrawerDissect.git
cd DrawerDissect
python -m venv dissectenv
source ./dissectenv/bin/activate
```

Windows
```sh
git clone https://github.com/EGPostema/DrawerDissect.git
cd DrawerDissect
python -m venv dissectenv
.\dissectenv\Scripts\activate
```

**2. Install PyTorch (local deployment only)**

If you plan to run models locally on your own hardware, install PyTorch *before* the next step. The correct version depends on your hardware:

```bash
# NVIDIA GPU (Windows/Linux)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Apple Silicon (Mac M1/M2/M3)
pip install torch torchvision

# CPU only
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Skip this step if using Roboflow cloud deployment.

**3. Install dependencies**

```sh
pip install -r requirements.txt
```

**4. Configure API keys**

DrawerDissect checks for API keys in two places, in this order:

*Option 1: Environment variables (recommended)*

Unix systems (Mac, Linux)
```bash
export ANTHROPIC_API_KEY="your_anthropic_key_here"
export ROBOFLOW_API_KEY="your_roboflow_key_here"
```

Windows
```bash
$env:ANTHROPIC_API_KEY="your_anthropic_key_here"
$env:ROBOFLOW_API_KEY="your_roboflow_key_here"
```

*Option 2: Direct configuration in `config.yaml`*

```yaml
api_keys:
  anthropic: "your_anthropic_key_here"
  roboflow: "your_roboflow_key_here"
```

---

## Deployment Options

DrawerDissect supports two modes for running computer vision models, switchable with a single line in `config.yaml`:

```yaml
deployment: "roboflow"  # or "local"
```

**Roboflow (cloud):** Runs models via the Roboflow API. Requires a Roboflow API key and internet connection. Easiest option to get started.

**Local:** Runs models directly on your machine using `.pt` weight files. No internet connection or Roboflow account required after setup. Pre-trained FMNH weights (last updated: 2025-03-04) are included in the `weights/` folder. See [Local YOLO Models](#-local-yolo-models) for details.

The compute device for local inference is detected automatically but can be overridden:

```yaml
local:
  device: "auto"   # auto-detect: CUDA > MPS > CPU (recommended)
  # device: "cpu"  # force CPU
  # device: "cuda" # force NVIDIA GPU
  # device: "mps"  # force Apple Silicon GPU
```

To verify your GPU is detected:
```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

### Performance Comparison

Benchmarks recorded processing a single drawer of 316 specimens (19 trays):

| Deployment | Hardware | Time (seconds) |
|------------|----------|---------------|
| roboflow | Roboflow Cloud (API) | 232.7 |
| local: cuda | NVIDIA GeForce RTX 4060 | 174.1 |
| local: cpu | AMD Ryzen 7 7800X3D | 214.1 |

> **Note:** CPU times vary significantly by processor. CPU-only deployment is not recommended for processing large numbers of drawers.

---

## Adding Images

Place all drawer images in the `drawers/unsorted` folder:

```
DrawerDissect/
├── drawers/
│   └── unsorted/              <- Place your drawer images here
│       ├── drawer_001.tif
│       ├── drawer_002.tif
│       └── drawer_003.jpg
```

When you run the pipeline, DrawerDissect will automatically generate an organized directory:

```
DrawerDissect/
├── drawers/
│   ├── unsorted/                empty after sorting
│   ├── drawer_001/
│   │   ├── fullsize/            original images
│   │   ├── resized/             resized drawer images
│   │   ├── trays/               individual tray images
│   │   ├── resized_trays/       resized tray images
│   │   ├── labels/              cropped tray text images
│   │   ├── guides/              tray maps
│   │   ├── specimens/           specimen images
│   │   ├── measurements/        size data & dimension maps
│   │   ├── masks/               specimen masks
│   │   ├── transparencies/      fully masked specimens (transparent bg)
│   │   ├── whitebg_specimens/   fully masked specimens (white bg)
│   │   ├── transcriptions/      text transcriptions
│   │   └── data/                final datasheets
│   └── drawer_002/
│       └── ... (same structure)
```

---

## Running the Pipeline

### Basic Usage

Process all images with default settings:

```bash
python process_images.py all
```

### Test with Sample Image

Download and test with sample image:

```bash
# For Mac/Linux:
curl -L -o drawers/unsorted/FMNH_cicindelidae_34_5_7.jpg https://github.com/EGPostema/DrawerDissect/releases/download/v0.1.0/FMNH_cicindelidae_34_5_7.jpg

# For Windows cmd:
curl -L -o "drawers/unsorted/FMNH_cicindelidae_34_5_7.jpg" "https://github.com/EGPostema/DrawerDissect/releases/download/v0.1.0/FMNH_cicindelidae_34_5_7.jpg"

# For Windows Powershell:
iwr "https://github.com/EGPostema/DrawerDissect/releases/download/v0.1.0/FMNH_cicindelidae_34_5_7.jpg" -OutFile "drawers/unsorted/FMNH_cicindelidae_34_5_7.jpg"

# Run the pipeline:
python process_images.py all
```

If automatic download fails, manually download from the link above, place in `drawers/unsorted/`, and run `python process_images.py all`.

### Advanced Usage

**Process specific drawer(s):**
```bash
python process_images.py all --drawers drawer_001
python process_images.py all --drawers drawer_001,drawer_005
```

**Run individual step(s):**
```bash
python process_images.py resize_drawers
python process_images.py find_trays measure_specimens
```

**Run step ranges:**
```bash
python process_images.py --from crop_specimens --until measure_specimens
python process_images.py --from create_masks  # from create_masks to end
python process_images.py --until crop_trays   # from start to crop_trays
```

**Combine flags for custom workflows:**
```bash
python process_images.py transcribe_speclabels --from find_specimens --until create_transparencies --drawers drawer_03,drawer_08
```
This command would run all steps from find_specimens to create_transparencies, and then transcribe_speclabels, for drawer_03 & drawer_08.

### List of Available Steps

```
all                    # Runs all steps in the order below
resize_drawers         # Resize large drawer images
find_trays             # Detect trays in drawer images
crop_trays             # Crop individual tray images
resize_trays           # Resize tray images
find_traylabels        # Detect label text in trays
crop_labels            # Crop tray label text
find_specimens         # Detect specimens in tray images
crop_specimens         # Crop specimen images
create_traymaps        # Create specimen location maps
outline_specimens      # Outline specimens
create_masks           # Create binary masks from outlines
fix_masks              # Clean up mask artifacts
measure_specimens      # Measure specimen masks
censor_background      # Remove backgrounds from specimens
outline_pins           # Outline specimen pins
create_pinmask         # Combine specimen and pin masks
create_transparency    # Create final masked specimen images
transcribe_barcodes    # Read barcode numbers (if enabled)
transcribe_geocodes    # Read geocode letters (if enabled)
transcribe_taxonomy    # Read taxonomic names (if enabled)
transcribe_speclabels  # Read specimen labels (if enabled)
validate_speclabels    # Validate specimen transcriptions
merge_data             # Combine all data into final CSVs
```

### Rerunning Steps

Use the --rerun flag to redo steps, overwriting previous outputs

```bash
python process_images.py {step} --rerun                                             # reruns {step} for all drawers
python process_images.py {step} --rerun --drawers drawer_001                        # reruns {step} for specific drawer(s)
python process_images.py --from {step} --until {step} --rerun --drawers drawer_001  # reruns range of steps for specific drawer(s)
```
![Screenshot 2025-07-09 142726](https://github.com/user-attachments/assets/08ba4c7f-a53b-4739-8016-9e20e0d44f52)

### Status Report

```bash
python process_images.py --status
python process_images.py --status --write-report  # creates a timestamped CSV for the report
```

![Screenshot 2025-07-09 142902](https://github.com/user-attachments/assets/63e64440-4911-4a52-99b6-5d83160245ed)

### Specimen-Only Projects

To start with specimen images rather than whole-drawer images:
- In `drawers`, create the folders `{your_folder_name}\specimens`
- Add specimen images to `{your_folder_name}\specimens`
- Run specimen-specific steps, e.g.:

```bash
python process_images.py --drawers {your_folder_name} --from outline_specimens --until create_transparency
```

---

## Example Outputs

### Specimen Locations in Trays

<img src="https://github.com/user-attachments/assets/ea8322a6-a4a6-468a-a744-451136f762a1" width="500">

### Tray-Level Transcriptions

<img src="https://github.com/user-attachments/assets/6ffe77b4-351f-4dc5-8fce-69f5226125af" height="250"> <img src="https://github.com/user-attachments/assets/2cbae42b-c04c-4bb0-a456-659cc367cb39" width="300">

| taxonomy | barcode | geocode |
|--------|----|----|
| <i>Cicindela (Cicindela) formosa gibsoni</i> | 57377 | NEA |
| <i>Automeris io</i> | - | - |

### Individual Specimen Images

<img src="https://github.com/user-attachments/assets/cef073ca-596a-4f2f-bb25-31c782b72945" height="200"> <img src="https://github.com/user-attachments/assets/acdb39bf-9a75-4812-8f07-32ac2a60fc7e" height="200"> <img src="https://github.com/user-attachments/assets/038e68c2-fd81-4374-9748-ea1d5c392bb8" height="200"> 

<img src="https://github.com/user-attachments/assets/ce2c569d-a180-4828-a857-042dfeab77ea" height="200">  <img src="https://github.com/user-attachments/assets/e2666020-7062-4d9c-b884-58f17f2dd29c" height="200">

### Masked Specimens

<img src="https://github.com/user-attachments/assets/8735f8de-f3e2-4750-b0a8-14e53bba44cb" height="200"> <img src="https://github.com/user-attachments/assets/6db89295-0b42-47cb-9152-695e1c4747e2" height="200"> <img src="https://github.com/user-attachments/assets/6c1cf238-229a-4185-b878-d471b304b0f6" height="200"> 

<img src="https://github.com/user-attachments/assets/697c5c1e-8015-43a0-9619-c74a4db8a8b5" height="200">  <img src="https://github.com/user-attachments/assets/acba309b-c3fd-4b84-9e4b-5ad5a9a9000c" height="200">

### Measurements

<img src="https://github.com/user-attachments/assets/d28be360-914c-496d-b013-affe98211588" height="300">

| length (mm) | width (mm) | area (mm2) |
|--------|----|----|
| 17.8 | 6.3 | 84.9 |

### Specimen-level Transcriptions

<img src="https://github.com/user-attachments/assets/3b45f583-d0f8-450c-853a-bc95e537e056" height="500">

### Summary Data

```
drawer01/
├── data/
│   ├── merged_data_02_05_2025_11_03/    # timestamped folder
│   │   ├── drawers.csv                  # drawer-level summary
│   │   ├── trays.csv                    # tray-level summary
│   │   ├── specimens.csv                # fully merged dataset
│   │   └── data_inputs/                 # contains all csvs used for summaries
│   │       ├── measurements.csv
│   │       ├── taxonomy.csv
│   │       ├── unit_barcodes.csv
│   │       └── location_checked.csv
│   └── merged_data_01_05_2025_14_22/    # timestamped folder from previous run
│       └── ... (same files)
```

---

## User Settings

Key aspects of the pipeline can be adjusted by directly editing the `config.yaml`:

```
DrawerDissect/
├── config.yaml  <- EDIT SETTINGS HERE
└── ...
```

### Toggle Steps

Turn on/off specific steps:

```yaml
processing:
  measurement_visualizations: "rand_sample"  # "on", "off", or "rand_sample" (max. 20 random measurement maps)
  transcribe_barcodes: false  # Set to true for tray-level barcodes
  transcribe_geocodes: false  # Set to true for tray-level geocodes
  transcribe_taxonomy: true  # Set to false to skip taxonomy transcription
  transcribe_specimen_labels: false  # Set to true for specimen label transcription (experimental)
```

Example settings:

<img src="https://github.com/user-attachments/assets/6ffe77b4-351f-4dc5-8fce-69f5226125af" height="250"> <img src="https://github.com/user-attachments/assets/2cbae42b-c04c-4bb0-a456-659cc367cb39" width="300">

| tray | transcribe_barcodes | transcribe_geocodes | transcribe_taxonomy|
|--------|----|----|----|
| tiger beetles | true | true | true |
| moth | false | false | true |

### Edit Models

📝 **Claude**

```yaml
claude:
  model: "claude-sonnet-4-20250514"  # substitute with any Claude model
  max_tokens: 600  # increase for complicated tasks, decrease for simpler tasks
```

📷 **Field Museum Roboflow Models (Default)**

Uses pre-trained FMNH models - these defaults will work in most cases:

```yaml
roboflow:
  workspace: "field-museum"
  models:
    drawer:
      endpoint: "trayfinder-base" # obj detection, finds trays in drawers
      version: 2
      confidence: 50 # adjustable, set from 1-99 (higher = greater threshold for predictions)
      overlap: 50 # adjustable, set from 1-99 (higher = more overlap allowed, obj detection only)
    tray:
      endpoint: "bugfinder-kdn9e" # obj detection, finds specimens in trays
      version: 16
      confidence: 50
      overlap: 50
    label:
      endpoint: "labelfinder" # obj detection, finds tray-level text info
      version: 7
      confidence: 50
      overlap: 50
    mask:
      endpoint: "bugmasker-all"  # segmentation, outlines specimen bodies
      version: 8 
      confidence: 50
    pin:
      endpoint: "pinmasker" # segmentation, outlines pins
      version: 6
      confidence: 50
```

The most up-to-date FMNH models can be found at [https://universe.roboflow.com/field-museum/](https://universe.roboflow.com/field-museum/). To find the endpoint and version number, select your model, go to Deploy > Model, and copy the values into `config.yaml`.

<img height="1000" alt="image" src="https://github.com/user-attachments/assets/df32c043-f4a1-49b7-8e9f-5dc7b5b7ebc8" />

📷 **Use Your Own Roboflow Models**

Simply replace our models with yours:

```yaml
roboflow:
  workspace: "YOUR_WORKSPACE"
  models:
    drawer:
      endpoint: "YOUR_DRAWER_MODEL"
      version: 1
      confidence: 50
      overlap: 50
    # ... (configure all 5 model types)
```

🤖 **Local YOLO Models**

Pre-trained FMNH weights (last updated: 2026-03-04) are included in the `weights/` folder:

```
weights/
├── drawer/   trayfinderpopupv17.pt
├── tray/     bugfinderkdn9ev20.pt
├── label/    labelfinderv8.pt
├── mask/     bugmaskerv12.pt
└── pin/      pinmaskerv6.pt
```

Set `deployment: "local"` in `config.yaml` to use them. Files are detected automatically with no additional configuration needed, unless you have multiple `.pt` files in the same folder:

```yaml
local:
  models:
    drawer: # optional: specify filename if folder contains multiple .pt files
    tray:
    label:
    mask:
    pin:
```

To use your own YOLO weights, replace the files in the `weights/` subfolders. The images and annotations for all FMNH models are available for download and retraining at [https://universe.roboflow.com/field-museum/](https://universe.roboflow.com/field-museum/).

To download training data:
- Select the desired model
- Select 'Dataset' under 'Data'
- Choose a version and click 'Download Dataset'

<img height="1000" alt="image" src="https://github.com/user-attachments/assets/ad8d7054-d678-4fe7-aad6-b96c227a2107" />

### Edit LLM Prompts

```yaml
prompts:
  barcode: # prompt for transcribing barcodes
    system: |
      You are a barcode reading tool. You should output only the numbers found in the image.
      The barcode always starts with an 8 and is five digits long. 
      If no valid barcode is found, output 'none'.
    user: |
      Read the barcode number. Output only the code, no explanations.
  
  geocode: # prompt for recognizing 3-letter geocodes
    system: |
      You are a geocode recognition tool for natural history specimens. 
      Your task is to identify the 3-letter geocode visible in the image.
      
      The geocode is always a 3-letter code (all capital letters):
      - "NEO"
      - "PAL"
      - "NEA"
      - "AFR"
      - "ORI"
      - "AUS"
      - "PAC"
      
      Output only the 3-letter geocode. If no valid 3-letter geocode is visible 
      or if the text is unclear, output 'UNK' (Unknown).
    user: |
      Identify the 3-letter geocode visible in this image. Output only the code (e.g., NEO, PAL), no explanations.
    
  taxonomy: # prompt for transcribing and organizing taxonomic IDs
    system: |
      You are a taxonomic label transcription tool specializing in natural 
      history specimens. Your task is to:
      1. Provide a complete transcription of the entire label, which may be handwritten
      2. Extract the taxonomic name, including any genus, subgenus, species, 
         and subspecies information
      3. If ONLY higher order taxonomic information is available (family -dae, tribe -ini, subfamily -nae), report this in 'taxonomy'
      4. Extract the taxonomic authority (author and/or year)

      For missing elements, output 'none'. Format your response as a structured 
      dictionary with these three keys:
      {
        'full_transcription': 'complete text as shown',
        'taxonomy': 'only taxonomic name (Genus (Subgenus) species subspecies) OR higher-order taxonomy', 
        'authority': 'author, year'
      }
    user: |
      Transcribe this taxonomic label, preserving the exact text and extracting 
      the taxonomic name and authority. Output only the dictionary, no explanations.
  
  specimen_label: # prompt for transcribing any visible text, verbatim, from specimen labels
    system: |
     You are a natural history specimen label transcription tool specializing in precise, verbatim transcription. Your task is to:
          1. Transcribe ALL visible text exactly as it appears, including:
             - Unclear, handwritten, or partially visible text
          2. Do not interpret, correct, or standardize any text
          3. Most text will be horizontal, read left-to-right. 
          4. Occasionally, text may be vertical or upside-down.
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
        }
    user: |
      Validate this location data:
      Transcribed text: {transcribed_text}
      Proposed location: {proposed_location}
```

### Performance Settings

Adjust memory usage and processing speed:

```yaml
resources:
  memory:
    sequential: false    # true = process one image at a time (good for large-image steps)
    max_workers: null    # null = automatic (uses half CPU cores), or set number
    batch_size: null     # process in smaller batches if needed
```

---

## Troubleshooting

**Pipeline won't start?**
- Ensure API keys are configured (either via environment variables or in `config.yaml`)
- For local deployments, ensure `.pt` files are in the correct `weights/` subfolder
- Check that the virtual environment is activated (`dissectenv`) with required packages installed (`pip install -r requirements.txt`)
- Check your current directory (`cd`); it should be `DrawerDissect`

**Models not performing well?**
- Adjust confidence/overlap thresholds
- Check image quality (small or low-resolution images may underperform)
- Performance may vary for different taxa
- Try older model versions or add new training data to update a model

**Transcription errors?**
- Verify API keys are correct and have sufficient credits
- Check internet connection for API calls
- Review and adjust prompts in `config.yaml` to match your text inputs

**Known Errors**
[COMING SOON]
