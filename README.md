# DrawerDissect

<img src="https://github.com/user-attachments/assets/26e883f0-f643-4715-80d6-abb2225bdb75" width="150" height="150" valign="middle"> 

---
**DrawerDissect** is an AI-driven pipeline for processing whole-drawer images of insect specimens. It can crop out specimen photos, measure specimens, transcribe various kinds of text, and create "masked" specimens for phenotypic analysis and species identification models.

>NEW: More advanced curation & databasing workflows are here!
>
>See the [README file in the advanced_functions folder](advanced_functions/README.md) for more information.

---

## Prerequisites
 
- [Python](https://www.python.org/downloads/) (ver. 3+)
- [Git](https://git-scm.com/downloads)
- An [Anthropic API key](https://support.anthropic.com/en/articles/8114521-how-can-i-access-the-anthropic-api) for reading tray and specimen labels
  - *not required when using [a local or non-Anthropic LLM](#llm-for-transcription)*
- A [Roboflow API key](https://docs.roboflow.com/api-reference/authentication)
  - *not required when using [local model weights](#computer-vision-models)*
- Supported image formats: TIF/TIFF, PNG, JPG/JPEG

DrawerDissect has run successfully on the following systems:
 
| System | OS | CPU | RAM | GPU |
|--------|----|----|-----|-----|
| MacBook Pro | macOS | 2.3 GHz Dual-Core Intel Core i5 | 8 GB | Intel Iris Plus Graphics 640 1536 MB |
| Mac mini | macOS | Apple M2 (8-core) | 16 GB | M2 Integrated (10-core) |
| Windows | Windows 11 | AMD Ryzen 7 7800X3D | 32 GB | NVIDIA GeForce RTX 4060 |
| Windows | Windows 11 | Intel i5-13400F | 32 GB | NVIDIA GeForce RTX 4060 |
 
Current Version: **v0.5.0**
 
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
 
**2. Install PyTorch/Ultralytics (local CV deployment only)**
 
If you plan to run computer vision models locally on your own hardware, install PyTorch *before* the next step. The correct version depends on your hardware:
 
```bash
# NVIDIA GPU (Windows/Linux)
## Check your CUDA version first
nvidia-smi

## Then install the right torchvision build
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124  # version >12.4
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121  # version 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118  # version 11.8

# Apple Silicon (Mac M1/M2/M3)
pip install torch torchvision
 
# CPU only
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```
 
Then install the local inference library:
 
```bash
pip install ultralytics
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
 
DrawerDissect uses AI for two distinct tasks, each configured independently in `config.yaml`:
 
- **Computer vision (CV) models** — detect trays, specimens, labels, and masks in images
- **Language model (LLM)** — reads and transcribes unit tray/specimen label text (when visible)
 
---
 
### Computer Vision Models
 
```yaml
deployment: "roboflow"  # or "local"
```
 
**Roboflow (cloud, DEFAULT):** Runs models via the Roboflow API. Requires a Roboflow API key and internet connection.
 
**Local:** Runs models directly on your machine using `.pt` weight files. No internet connection or Roboflow account required after setup. Pre-trained FMNH weights (last updated: 2026-05-04) are included in the `weights/` folder.
 
The processor used for CV inference is detected automatically by default, but can be overridden:
 
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
 
#### Performance Comparison
 
Benchmarks recorded processing a single drawer of 316 specimens (19 trays):
 
| Deployment | Hardware | Time (seconds) |
|------------|----------|---------------|
| roboflow | Roboflow Cloud (API) | 232.7 |
| local: cuda | NVIDIA GeForce RTX 4060 | 174.1 |
| local: cpu | AMD Ryzen 7 7800X3D | 214.1 |
 
> **Note:** CPU times will vary significantly by processor.
 
---
 
### LLM for Transcription
 
All transcription steps send images to a language model and expect structured text output in return. **Therefore, you must use a model that support vision tasks (image input)**. Text-only models will not work!

By default, DrawerDissect uses the Anthropic Claude API. You can switch to any OpenAI-compatible provider, including cloud alternatives and local models running on your own machine.

> *Currently, we have not benchmarked DrawerDissect for any non-Anthropic models. Results may vary; please feel free to share your experiences with us via the issues page.*
 
Configure the LLM in the `llm` section of `config.yaml`:
 
```yaml
llm:
  provider: "anthropic"       # "anthropic" or "openai_compatible"
  model: "claude-sonnet-4-6"  # change model name here
  max_tokens: 600             # default for simple transcription tasks
  temperature: 0              # 0 = most deterministic (least variable across multiple runs)
```
 
#### Option 1: Anthropic Claude (default)
 
Requires an Anthropic API key. Claude performs well on both printed and handwritten labels and handles the structured JSON output reliably.
 
```yaml
llm:
  provider: "anthropic"
  model: "claude-sonnet-4-6"
  max_tokens: 600
  temperature: 0
```
 
#### Option 2: Cloud alternatives
 
These providers offer OpenAI-compatible APIs and work by setting `provider: "openai_compatible"`. All require the OpenAI Python package (`pip install openai`) and an API key from the provider. All listed models support vision.
 
| Provider | Recommended model | base_url | Sign up |
|----------|------------------|----------|---------|
| OpenAI | `gpt-4o` | `https://api.openai.com/v1` | [platform.openai.com](https://platform.openai.com) |
| Google Gemini | `gemini-2.5-flash` | `https://generativelanguage.googleapis.com/v1beta/openai/` | [aistudio.google.com](https://aistudio.google.com) |
| Mistral | `mistral-medium-3.5` | `https://api.mistral.ai/v1` | [console.mistral.ai](https://console.mistral.ai) |
| DeepSeek | `deepseek-v4-pro` | `https://api.deepseek.com` | [platform.deepseek.com](https://platform.deepseek.com) |
 
Example — Google Gemini:
 
```yaml
llm:
  provider: "openai_compatible"
  model: "gemini-2.5-flash"
  max_tokens: 600
  temperature: 0
  openai_compatible:
    base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"
    api_key: "YOUR_GEMINI_API_KEY"
```
 
Example — OpenAI:
 
```yaml
llm:
  provider: "openai_compatible"
  model: "gpt-4o"
  max_tokens: 600
  temperature: 0
  openai_compatible:
    base_url: "https://api.openai.com/v1"
    api_key: "YOUR_OPENAI_API_KEY"
```
 
#### Option 3: Fully Open-Source Models (Ollama)
 
[Ollama](https://ollama.com) lets you run vision models entirely on your own machine for free, with no API key. Performance depends on your hardware.
 
**1. Install Ollama** from [ollama.com](https://ollama.com), then pull a vision-capable model:
 
```bash
ollama pull llama3.2-vision   # good general-purpose starting point (~8 GB)
ollama pull gemma3:9b         # lighter option, good instruction following (~6 GB)
ollama pull gemma4:e4b        # newest Google model, native multimodal (~6 GB)
ollama pull qwen2.5vl         # strong on dense text and documents (~varies by size)
```
 
**2. Configure `config.yaml`:**
 
```yaml
llm:
  provider: "openai_compatible"
  model: "llama3.2-vision"    # must match the name you used in ollama pull
  max_tokens: 600
  temperature: 0
  openai_compatible:
    base_url: "http://localhost:11434/v1"
    api_key: "ollama"         # required by the SDK but ignored by Ollama
```
 
**3. Make sure Ollama is running** before starting the pipeline (`ollama serve`, or it starts automatically on most systems after installation).
 
Other local server applications use the same pattern with a different `base_url`:
 
| Application | Default base_url |
|-------------|-----------------|
| Ollama | `http://localhost:11434/v1` |
| LM Studio | `http://localhost:1234/v1` |
| vLLM | `http://localhost:8000/v1` |
| Jan | `http://localhost:1337/v1` |
 
#### Choosing a model for this task
 
The transcription steps are demanding: labels are small, often handwritten, frequently rotated, and the model must output structured JSON covering multiple DarwinCore fields. A few practical notes:
 
- **Printed labels** (barcodes, geocodes, typed taxonomy): most vision models handle these well, including smaller local models.
- **Handwritten locality labels** (`transcribe_specimens`): this is the hardest case. Smaller local models (7–11B parameters) can struggle with historic cursive, faded ink, or heavily abbreviated text. If results are poor, try a larger local model or a cloud provider.
- **Structured JSON output**: the pipeline includes a corrective retry — if the model returns malformed JSON, it sends the bad output back and asks for a fix. This helps with models that add preamble text around their JSON. If a model consistently produces invalid output, try increasing `max_tokens` or switching models.
- **`max_tokens` for `transcribe_specimens`**: this step processes many images per call and generates long responses. The `max_tokens: 15000` in `traycontext_settings` is set separately from the `max_tokens: 600` in the `llm` section, which applies only to the simpler single-image steps (barcodes, geocodes, taxonomy). Do not reduce the `traycontext_settings` value significantly.
> All transcription results should be carefully validated before permanently databasing, regardless of which model is used.
 
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
│   │   │   ├── tray_labels/    tray-level (barcode, geocode, taxonomy)
│   │   │   └── tray_context/   specimen locality transcriptions
│   │   └── data/                final datasheets, timestamped
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
 
<i>This includes drawers that are in the 'unsorted' folder!</i>
 
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
python process_images.py transcribe_specimens --from find_specimens --until create_transparency --drawers drawer_03,drawer_08
```
This command would run all steps from find_specimens to create_transparency, and then transcribe_specimens, for drawer_03 & drawer_08.
 
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
transcribe_specimens   # Read specimen locality labels (if enabled)
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

> If your instution uses color-coded unit tray labels to represent biogeographic realm, [see our tool for color extraction/mapping](advanced_functions/README_labelcolor.md)!
 
### Individual Specimen Images
 
<img src="https://github.com/user-attachments/assets/cef073ca-596a-4f2f-bb25-31c782b72945" height="200"> <img src="https://github.com/user-attachments/assets/acdb39bf-9a75-4812-8f07-32ac2a60fc7e" height="200">
 
### Masked Specimens
 
<img src="https://github.com/user-attachments/assets/8735f8de-f3e2-4750-b0a8-14e53bba44cb" height="200"> <img src="https://github.com/user-attachments/assets/6db89295-0b42-47cb-9152-695e1c4747e2" height="200">
 
### Measurements
 
<img src="https://github.com/user-attachments/assets/d28be360-914c-496d-b013-affe98211588" height="300">

| length (mm) | width (mm) | area (mm2) |
|--------|----|----|
| 17.8 | 6.3 | 84.9 |
 
### Specimen Label Transcriptions
 
**NOTE: This step is meant to be an aid to metadata transcription, NOT a replacement for manual transcription; all results should be carefully validated before permanently databasing**
 
The `transcribe_specimens` step sends a combination of filtered specimen images, a full-tray reference image, and previously transcribed geocodes to the configured LLM to estimate label metadata from fragments of visible text in the specimen dorsal images.
 
**Pipeline flow:**
 
1. **Bugcleaner filtering**: A Roboflow classification model (`bugcleaner`) examines each specimen crop and classifies it as "text" or "notext".
   - Specimens classified as "notext" are skipped for the LLM API call.
   - The results are cached in `bugcleaner_results.csv`.
2. **Multi-crop API call**: For each tray, the LLM receives:
   - Tray header context (geocode) from earlier transcription steps, if available
   - A downsized tray overview image (optional, for spatial context)
   - Individual specimen crops
   - Trays with many specimens are batched
3. **Three-step transcription**:
   - The LLM transcribes each label independently,
   - parses text into DarwinCore fields,
   - then cross-references labels to find and group similar labels, based on visual & textual cues
<img width="666" height="354" alt="Screenshot 2026-03-24 154919" src="https://github.com/user-attachments/assets/e369078f-1253-4942-a197-159e4dd7b5ae" />
**Output:** `specimen_localities.csv` with one row per specimen containing:
 
| Field (* = DarwinCore) | Description |
|-------|-------------|
| tray | Tray identifier |
| specimen_id | Specimen identifier |
| label_group | Group number (specimens that may share a collecting event) |
| match_type | "identical", "similar", or "unique" |
| verbatim_text | Raw label text as transcribed |
| country*, stateProvince*, county*, municipality* | Parsed administrative geography |
| verbatimLocality* | Place description exactly as written on the label |
| locality* | Primary catch-all for named places, natural features, directional descriptions |
| waterBody*, islandGroup*, island* | Aquatic/island location |
| verbatimElevation* | Elevation exactly as written on the label |
| habitat* | Habitat type or description |
| samplingProtocol* | Collection method if mentioned |
| collector* | Collector name |
| verbatimEventDate* | Collection date exactly as written on the label |
| identifiedBy* | Person who identified the specimen |
| possibleName | Name or initials present on label but role unclear |
| verbatimCoordinates* | Coordinates exactly as written on the label |
| flags | Quality flags (e.g., geocode_mismatch, conflicting_info) |
| model | Model version used for transcription |
 
**Configuration:**
 
```yaml
traycontext_settings:
  bugcleaner_enabled: true             # set to false to skip bugcleaner filtering
  bugcleaner_confidence_threshold: 95  # minimum confidence for text detection
  max_tokens: 15000                    # max output tokens per API call
  include_tray_image: true             # send tray overview image for spatial context, can set 'false' to save tokens
  max_specimens_per_batch: 20          # split large trays into batches
```
 
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
│   │       ├── geocodes.csv
│   │       └── specimen_localities.csv
│   └── merged_data_01_05_2025_14_22/    # timestamped folder from previous run
│       └── ... (same files)
```

> To begin shaping data across drawers for permanent databasing (e.g. EMu, GBIF), see [instructions for advanced_functions](advanced_functions/README.md)!

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
# ------------------------------------------------------------
# Processing toggles
# ------------------------------------------------------------
processing:
  measurement_visualizations: "off"  # "on", "off", or "rand_sample" (max 20 random visualizations)
  transcribe_barcodes: false         # set to true for tray-level barcodes
  transcribe_geocodes: false         # set to true for tray-level geocodes
  transcribe_taxonomy: false         # set to true for taxonomic label transcription
  transcribe_specimens: false        # set to true for specimen label transcription helper
```
 
Example settings:
 
<img src="https://github.com/user-attachments/assets/6ffe77b4-351f-4dc5-8fce-69f5226125af" height="250"> <img src="https://github.com/user-attachments/assets/2cbae42b-c04c-4bb0-a456-659cc367cb39" width="300">
 
| tray | transcribe_barcodes | transcribe_geocodes | transcribe_taxonomy|
|--------|----|----|----|
| tiger beetles | true | true | true |
| moth | false | false | true |
 
### Edit CV Models
 
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
    bugcleaner:
      endpoint: "bugcleaner" # classification, detects text on specimen crops
      version: 3
```
 
The most up-to-date FMNH models can be found at [https://universe.roboflow.com/field-museum/](https://universe.roboflow.com/field-museum/). To find the endpoint and version number, select your model, go to Deploy > Model, and copy the values into `config.yaml`.
 
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
    # ... (configure all 6 model types)
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
 
To use your own YOLO weights, replace the files in the `weights/` subfolders. The images and annotations for all FMNH models are available for download and local training at [https://universe.roboflow.com/field-museum/](https://universe.roboflow.com/field-museum/).
 
To download training data:
- Select the desired model
- Select 'Dataset' under 'Data'
- Choose a version and click 'Download Dataset'
### Edit LLM Prompts
 
All prompts are configured in `config.yaml` under the `prompts` section. Each prompt has a `system` (instructions) and `user` (per-image request) component.
 
**Tray header prompts** (`barcode`, `geocode`, `taxonomy`) handle transcription of the printed labels at the top of each tray.
 
**Specimen label prompt** (`traycontext`) handles the multi-image transcription of specimen labels.
See [Specimen Label Transcriptions](#specimen-label-transcriptions) for details.
 
To customize prompts for your collection, edit the `system` and `user` fields in `config.yaml`.
 
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
- For local CV deployments, ensure `.pt` files are in the correct `weights/` subfolder
- Check that the virtual environment is activated (`dissectenv`) with required packages installed (`pip install -r requirements.txt`)
- Check your current directory (`cd`); it should be `DrawerDissect`
**Models not performing well?**
- Adjust confidence/overlap thresholds
- Check image quality (small or low-resolution images may underperform)
- Performance may vary for different taxa
- Try older model versions or add new training data to update a model (please open an Issue if there are taxa or a particular type of image you want us to add to the model!)
**Transcription errors?**
- Verify API keys are correct and have sufficient credits
- Check internet connection for API calls
- Ensure the configured LLM supports vision (image input), as text-only models will fail
- Review and adjust prompts in `config.yaml` to match your text inputs
