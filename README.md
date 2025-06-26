# <img src="https://github.com/user-attachments/assets/26e883f0-f643-4715-80d6-abb2225bdb75" width="75" height="75">rawerDissect

**DrawerDissect** is an AI-driven pipeline for processing whole-drawer images of insect specimens. It can extract individual specimen photos, measure specimens, transcribe visible text, and create "masked" specimens for downstream phenotypic analysis.

<img width="1000" src="https://github.com/user-attachments/assets/20e3abb8-18d4-45cd-9b83-3c67048e24b0" />

---

## Prerequisites

- [Python](https://www.python.org/downloads/) (ver. 3+)
- [Git](https://git-scm.com/downloads)
- API keys from:
  - [Roboflow](roboflow.com) - for detecting and segmenting specimens
  - [Anthropic](anthropic.com) - for reading tray and specimen labels
- Supported image formats: TIF/TIFF, PNG, JPG/JPEG

DrawerDissect has been successfully tested on the following systems:

| System | OS | CPU | RAM | GPU |
|--------|----|----|-----|-----|
| Mac | macOS | Apple M2 (8-core) | 16 GB | M2 Integrated (10-core) |
| Windows | Windows 11 | AMD Ryzen 7 7800X3D | 32 GB | NVIDIA GeForce RTX 4060 |
| Windows | Windows 11 | Intel i5-13400F | 32 GB | NVIDIA GeForce RTX 4060 |

---

## Installation

**Set Up Project in a Python Environment**

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

**Configure API Keys**

Open `config.yaml` in the main directory, and add your API keys:

```yaml
api_keys:
  anthropic: "YOUR_ANTHROPIC_KEY" # replace YOUR_ANTHROPIC_KEY with your key
  roboflow: "YOUR_ROBOFLOW_KEY" # replace YOUR_ROBOFLOW_KEY with your key
```

- [Get Anthropic API Key](https://support.anthropic.com/en/articles/8114521-how-can-i-access-the-anthropic-api)
- [Get Roboflow API Key](https://docs.roboflow.com/api-reference/authentication)

---

## 📁 Adding Images

Place all drawer images in the `drawers/unsorted` folder:

```
DrawerDissect/
├── drawers/
│   └── unsorted/          ← Place your drawer images here
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

## 🔧 Running the Pipeline

### Basic Usage

Process all images with default settings:

```bash
python process_images.py all
```

### Test with Sample Image

1. [Download test image](https://drive.google.com/drive/folders/1NHV9MSR-sjmAW43KlyPfSB9Xr5ZTvJFt?usp=drive_link)
2. Place in `drawers/unsorted/`
3. Run: `python process_images.py all`

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

---

## 📊 Example Outputs

[WIP]

---

## ⚙️ User Settings

Key aspects of the pipeline can be adjusted by directly editing the `config.yaml`:

```
DrawerDissect/
├── config.yaml  ← EDIT SETTINGS HERE
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

![image](https://github.com/user-attachments/assets/5639e133-3d36-4322-b879-a71e0ffe6858)


### Edit Models

📝 **Claude**

```yaml
claude:
  model: "claude-sonnet-4-20250514"  # subsitute with any claude model; speed, accuracy, and price may vary
  max_tokens: 600  # Default max tokens - increase for complicated tasks, decrease for simpler tasks
```

📷 **Field Museum Roboflow Models (Default & Recommended)**

Uses pre-trained FMNH models - these defaults will work in most cases:

```yaml
roboflow:
  workspace: "field-museum" # FMNH workspace is default
  models:
    drawer:
      endpoint: "trayfinder-base" # obj detection, finds trays in drawers
      version: 2
      confidence: 50 # adjustable, set from 1-99 (higher # = greater threshold for predictions)
      overlap: 50 # adjustable, set from 1-99 (higher # = higher overlap between objects, obj detection ONLY)
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
      endpoint: "pinmasker" # segmentation, outlines pin
      version: 6
      confidence: 50
```

The most up-to-date FMNH models can be found at: https://app.roboflow.com/field-museum

📷 **Use Your Own Roboflow Models**

Simply replace our models with yours:

```yaml
roboflow:
  workspace: "YOUR_WORKSPACE" # add your workspace here
  models:
    drawer:
      endpoint: "YOUR_DRAWER_MODEL" # add model ID here
      version: 1
      confidence: 50 # adjustable, set from 1-99 (higher # = greater threshold for predictions)
      overlap: 50 # adjustable, set from 1-99 (higher # = higher overlap between objects, obj detection ONLY)
    # ... (configure all 5 model types)
```

⚠️ Pipeline may fail to run if any models are missing ⚠️

🤖 **Open-Source Alternatives**

Our training data for all FMNH models can be downloaded to train open-source models at: [LINK COMING SOON]

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
    sequential: false    # true = process one image at a time (slower, less memory, good for large-image steps)
    max_workers: null    # null = automatic (uses half CPU cores), or set number
    batch_size: null     # Process in smaller batches if needed
```

## 📋 Troubleshooting

**Pipeline won't start?**
- [ ] API keys added to `config.yaml` and file saved
- [ ] Virtual environment activated (`dissectenv`)
- [ ] All packages installed (`pip install -r requirements.txt`)
- [ ] Images placed in `drawers/unsorted/` folder

**Out of memory errors?**
- Use `--sequential` flag to process one image at a time
- Reduce `--max-workers` to limit parallel processing
- Use `--batch-size` to process smaller groups

**Models not detecting properly?**
- Adjust confidence thresholds: `--tray_confidence 30` (lower = more detections)
- Check image quality and format
- Performance may vary for different taxa

**Transcription errors?**
- Verify API keys are correct and have sufficient credits
- Check internet connection for API calls
- Review and adjust prompts in `config.yaml` if needed
