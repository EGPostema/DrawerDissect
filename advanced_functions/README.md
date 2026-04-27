# label_color_classifier.py

Detects unit tray label background color and assigns a biogeographic realm code, writing results into DrawerDissect's standard transcription folder for automatic pickup by the merge step.

---

## Usage

First, set up drawerdissect, and then run all steps as usual ```--until crop_traylabels``` to produce cropped unit tray label images.

Then, run the command to extract color values & assign geocodes:

```bash
# Single drawer
python advanced_functions/label_color_classifier.py --drawer Cicindelidae_Drawer

# Multiple drawers
python advanced_functions/label_color_classifier.py --drawer Cicindelidae_Drawer,Cleridae_Drawer

# All drawers
python advanced_functions/label_color_classifier.py --all

# All drawers matching a prefix
python advanced_functions/label_color_classifier.py --all --prefix Cicindelidae

# Overwrite existing geocodes.csv
python advanced_functions/label_color_classifier.py --drawer Cicindelidae_Drawer --rerun
```

Then, all drawerdissect steps can be run as usual (including ```merge_data```), **but be sure to have ```transcribe_geocodes``` set to ```FALSE``` in the config YAML**

```
DrawerDissect_root/
│
├── drawers/
│   └── Cicindelidae_Drawer/
│       ├── labels/
│       │   ├── 01/
│       │   │   └── Cicindelidae_Drawer_tray_01_label.jpg  ← input (from DrawerDissect)
│       │   └── 02/
│       │       └── Cicindelidae_Drawer_tray_02_label.jpg
│       │
│       └── transcriptions/
│           └── tray_labels/
│               ├── taxonomy.csv
│               ├── unit_barcodes.csv
│               └── geocodes.csv                           ← written by this script
│
└── advanced_functions/
    └── label_color_classifier.py
```

`geocodes.csv` schema:
```
tray_id,                     geocode, hue_deg, sat,   avg_r, avg_g, avg_b
Cicindelidae_Drawer_tray_01, NEA,     199.3,   0.192, 103,   120,   128
```
The color columns (`hue_deg`, `sat`, `avg_r/g/b`) are for reference and are dropped by merge.

Geocode values follow the DrawerDissect standard: `NEA`, `NEO`, `PAL`, `AFR`, `ORI`, `AUS`, `PAC`. Unrecognised label colors are assigned `UNK`.

---

## Correcting a misclassified tray

Edit `geocodes.csv` directly — it's a plain CSV. Change the `geocode` value for the relevant `tray_id` and save. The corrected value will be used on the next merge run.

---

## Adding or adjusting color bins

Color bins are defined in `REALM_MAP` near the top of the script:

```python
REALM_MAP = [
    # Code   hue_deg  hue_tol  min_sat  max_sat   # label colour / realm
    ("NEA",  199.3,   35.0,   0.05,    1.00),    # muted blue       / Nearctic
    ("NEO",  141.2,   35.0,   0.05,    1.00),    # muted green      / Neotropical
    ("AUS",  348.7,   35.0,   0.05,    0.30),    # muted pink       / Australasian
    ("PAL",  346.7,   20.0,   0.30,    1.00),    # dark pink/red    / Palearctic
    ("AFR",   34.6,   20.0,   0.45,    1.00),    # saturated orange / Afrotropical
    ("ORI",   51.0,   25.0,   0.20,    1.00),    # muted yellow     / Oriental
    # ("PAC", ???,   35.0,   0.05,    1.00),     # not yet calibrated
]
```

- **`hue_deg`** — target hue angle (0–360°): blue ~200°, green ~140°, pink ~350°, orange ~35°, yellow ~50°
- **`hue_tol`** — degrees either side that still match; tighten if two colors are colliding
- **`min_sat` / `max_sat`** — saturation bounds (0–1); used to separate colors that share a hue (PAL and AUS are both ~347° but differ in saturation)

### Adding a new color (e.g. PAC)

**Step 1.** Run `--calibrate` on a known label crop:

```bash
python advanced_functions/label_color_classifier.py --calibrate "path/to/label.jpg" Pacific
```

Output:
```
Calibration — 'Pacific'
  hue_deg : 172.4°
  sat     : 0.083

Suggested REALM_MAP entry (replace XXX with the 3-letter code):
    ("XXX", 172.4, 25.0, 0.04),  # <colour> / Pacific
```

**Step 2.** Replace the commented-out `PAC` stub in `REALM_MAP` with the new entry:

```python
    ("PAC",  172.4,  25.0,   0.04,    1.00),   # muted ??? / Oceanian
```

**Step 3.** Re-run with `--rerun` to reclassify all trays:

```bash
python advanced_functions/label_color_classifier.py --all --rerun
```
