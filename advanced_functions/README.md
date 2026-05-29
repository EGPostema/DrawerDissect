# DrawerDissect Advanced Functions

This folder contains the **post-pipeline tooling** for DrawerDissect: scripts
that take the per-drawer outputs of `process_images.py`, aggregates them across
drawers, loops in human curation, and produce repository-ready spreadsheets
for upload to EMu, GBIF, and elsewhere.

It also contains a tool for automatically processing unit tray labels 
with color-coded biogeographical realms ([see instructions here](advanced_functions/README_labelcolor.md))

If you've never run DrawerDissect's main pipeline, start with the project's
[top-level README](README.md) first. This document assumes you have at least one drawer
that has finished processing and produced output in `drawers/<drawer_id>/`.

---

## Contents

1. [Overall workflow](#1-overall-workflow)
2. [Quick reference](#2-quick-reference)
3. [Folder structure](#3-folder-structure)
4. [First-time walkthrough](#4-first-time-walkthrough)
5. [Per-script reference](#5-per-script-reference)
   - [`master_merge.py`](#master_mergepy)
   - [`scaffold_barcodes.py`](#scaffold_barcodespy)
   - [`scaffold_locations.py`](#scaffold_locationspy)
   - [`emu_format.py`](#emu_formatpy)
   - [`gbif_format.py`](#gbif_formatpy)
   - [`sort_specimens.py`](#sort_specimenspy)
   - [`archive_drawers.py`](#archive_drawerspy)

---

## 1. Overall workflow

DrawerDissect's advanced functions follow a linear flow from raw pipeline
output → human curation → repository upload formats. The diagram below shows
how data moves through the system.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       PER-DRAWER PIPELINE (existing)                     │
│                                                                          │
│   python process_images.py --drawer <drawer_id>                          │
│                                                                          │ 
│   Outputs to drawers/<drawer_id>/:                                       │    
│     specimen images, masks, and data                                     │    
│     (data stored in: data/merged_data_<timestamp>/)                      │    
└──────────────────────────────────────────────────────────────────────────┘    
                                   │                                            
                                   ▼                                            
┌──────────────────────────────────────────────────────────────────────────┐    
│                       CROSS-DRAWER AGGREGATION                           │    
│                                                                          │    
│   python master_merge.py --prefix <drawer_prefix>                        │
│                                                                          │────┐  sort images
│   Outputs to master_data/master_<prefix>_<timestamp>/:                   │    │  by species
│     master_specimens.csv, master_trays.csv, master_drawers.csv           │    │      │
│     master_inputs/  (taxonomy, barcodes, geocodes, localities,           │    │      ▼
│                      measurements, bugcleaner_results)                   │    │
└──────────────────────────────────────────────────────────────────────────┘    │
                                   │                                            │
                                   ▼                                            │
┌──────────────────────────────────────────────────────────────────────────┐    │
│                       CREATE CURATION SCAFFOLDING                        │    │
│                                                                          │    │
│   python advanced_functions/scaffold_barcodes.py                         │    │
│       --master_dir master_data/master_<...>                              │    │
│                                                                          │    │
│   python advanced_functions/scaffold_locations.py                        │    │
│       --master_dir master_data/master_<...>                              │    │
│                                                                          │    │
│   Appends new rows (one per specimen) to:                                │    │
│     curation/specimen_barcodes.csv                                       │    │
│     curation/checked_locations.csv                                       │    │
└──────────────────────────────────────────────────────────────────────────┘    │
                                   │                                            │                 
                                   ▼                                            │
┌──────────────────────────────────────────────────────────────────────────┐    │
│                       MANUAL CURATION (CSV)                              │    │
│                                                                          │    │
│   curation/specimen_barcodes.csv:                                        │    │
│     - Fill in institution-specifc, specimen-level barcodes               │    │
│                                                                          │    │
│   curation/checked_locations.csv:                                        │    │
│     - Validate LLM-parsed fields & fill in missing information           │    │
│     - Set approved=yes for validated rows                                │    │
└──────────────────────────────────────────────────────────────────────────┘    │
                                   │                                            │
        ┌──────────────────────────┘                          ┌─────────────────┘
        │                          │                          │
        ▼                          ▼                          ▼
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐
│   EMU FORMAT       │  │   GBIF FORMAT      │  │  SORT SPECIMENS        │
│                    │  │                    │  │                        │
│   emu_format.py    │  │   gbif_format.py   │  │  sort_specimens.py     │
│   --master_dir <…> │  │   --master_dir <…> │  │   --master_dir <…>     │
│                    │  │                    │  │                        │
│   Outputs:         │  │   Outputs:         │  │  Outputs:              │
│     emu_catalog    │  │     occurrence     │  │   train/valid/test     │
│     emu_pending    │  │     gbif_pending   │  │   manifest.csv         │
│     multimedia/    │  │     run_log        │  │   run_log              │
│     run_log        │  │                    │  │                        │
└────────────────────┘  └────────────────────┘  └────────────────────────┘
        │                          │                          │
        ▼                          ▼                          ▼
┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐
│  manual emu import │  │ manual gbif import │  │ train species ID model │
└────────────────────┘  └────────────────────┘  └────────────────────────┘
        │                          │
        └──────────────┬───────────┘
                       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       ARCHIVE (when ready)                               │
│                                                                          │
│   python advanced_functions/archive_drawers.py                           │
│       --prefix <drawer_prefix>                                           │
│                                                                          │
│   Compresses drawer folders to archive/<drawer_id>.zip                   │
│   Deletes the originals after the zip is verified.                       │
│   Restore later with --restore --prefix <...> if needed.                 │
└──────────────────────────────────────────────────────────────────────────┘
```

**Key principle:** the `curation/` folder is the source of truth for human-
validated data for repository uploads (EMu, GBIF). `sort_specimens.py` is a
separate downstream branch that doesn't require curation — any specimen with
a taxonomy and an image goes in.

---

## 2. Quick reference

| I want to... | Run this |
|---|---|
| Aggregate a specific drawer/set of drawer's outputs | `python advanced_functions/master_merge.py --prefix <drawer_prefix>` |
| Aggregate everything | `python advanced_functions/master_merge.py` |
| Generate barcode entry sheet | `python advanced_functions/scaffold_barcodes.py --master_dir master_data/master_<...>` |
| Generate locality validation sheet | `python advanced_functions/scaffold_locations.py --master_dir master_data/master_<...>` |
| Build EMu upload | `python advanced_functions/emu_format.py --master_dir master_data/master_<...>` |
| Build GBIF upload | `python advanced_functions/gbif_format.py --master_dir master_data/master_<...>` |
| Build classification training set | `python advanced_functions/sort_specimens.py --master_dir master_data/master_<...>` |
| Archive completed drawers | `python advanced_functions/archive_drawers.py --prefix <drawer_prefix>` |
| Restore an archived drawer | `python advanced_functions/archive_drawers.py --restore --prefix <drawer_prefix>` |

**Common shared conventions:**
- All scripts that filter by drawer accept `--prefix` (one or more space-separated values), matching drawers whose folder names begin with that string.
  - This can be used to get single drawers, specific sets of drawers, OR sets of drawers that share a common prefix (e.g. Cicindelidae_)
- Scripts that read aggregated data require `--master_dir <PATH>` pointing at a specific `master_<...>` folder.
- Output folders are timestamped (`YYYY-MM-DD-HH-MM`) so re-runs never overwrite each other.

---

## 3. Folder structure

After you've done a few runs, your project will look something like this:

```
drawerdissect/
│
├── drawers/                             # raw input + per-drawer pipeline output
│   ├── cicindelidae_34_4_10/
│   ├── Cleridae_Drawer/
│   └── ...
│
├── master_data/                              # cross-drawer aggregations (regenerable)
│   ├── master_cicindelidae_2026-04-30-14-23/ # results for prefix 'cicindelidae_'
│   ├── master_2026-05-12-09-00/              # results from all projects in drawers/
│   └── ...
│
├── curation/                            # place for human-filled/-verified metadata
│   ├── specimen_barcodes.csv
│   └── checked_locations.csv
│
├── advanced_outputs/                    # downstream deliverables
│   ├── emu_upload/                      # emu-shaped data
│   │   └── emu_<prefix>_<timestamp>/
│   ├── gbif_upload/                     # gbif-shaped data
│   │   └── gbif_<prefix>_<timestamp>/
│   └── classification_splits/           # images ready for training species ID models
│       └── <run_name>/
│
└── archive/                             # zipped completed drawers
    ├── hymenoptera_5.zip
    └── ...
```

>**The `curation/` folder is the only one with irreplaceable human work.** Every
other folder can be regenerated by re-running scripts. We recommend backing this folder up periodically
to a separate location (cloud, external drive, etc.).

---

## 4. First-time walkthrough

A complete walk-through of processing one drawer from pipeline output to
upload-ready files. Once you've done this once, the per-script reference
below covers anything else you need.

Suppose you've just finished running `process_images.py` on the drawer
`cicindelidae_34_4_10` and want to push it to EMu and GBIF.

### Step 1: Aggregate drawer outputs

```
python master_merge.py --prefix cicindelidae_34_4_10
```

This produces a folder like `master_data/master_cicindelidae_34_4_10_2026-04-30-18-38/`
containing the consolidated CSVs. 
**Copy the path that gets printed** at the end of the run, as you'll need it for
every subsequent step.

### Step 2: Generate barcode entry sheet & manually fill

```
python advanced_functions/scaffold_barcodes.py --master_dir master_data/master_cicindelidae_34_4_10_2026-04-30-18-38
```

This appends rows to `curation/specimen_barcodes.csv` (one per specimen).
The `FMNH-INS#` column starts blank for new specimens. As barcodes are read (or added to specimens) we recommend 
using DrawerDissect's traymaps to make sure full_id (DrawerDissect) and barcode # (physical number on specimen) are matched

### Step 3: Generate locality validation sheet

```
python advanced_functions/scaffold_locations.py --master_dir master_data/master_cicindelidae_34_4_10_2026-04-30-18-38
```

This appends rows to `curation/checked_locations.csv` with the LLM's parsed
locality fields pre-filled to augment manual metadata transcription.

**Set `approved` to `yes` when you're confident in a row**

### Step 4: Build EMu and/or GBIF uploads

```
python advanced_functions/emu_format.py --master_dir master_data/master_cicindelidae_34_4_10_2026-04-30-18-38
python advanced_functions/gbif_format.py --master_dir master_data/master_cicindelidae_34_4_10_2026-04-30-18-38
```

Each produces a timestamped folder under `advanced_outputs/`. Specimens that
pass all gates (have a specimen barcode/ID number, have an approved location, have a
scientific name) end up in the catalog file. Everything else lands in a
pending file with reasons listed.

### Step 5: Upload (manual)

Go through your institution's steps for bulk uploading to EMu or GBIF.

### Step 6: Archive when done

After everything has been uploaded successfully:

```
python advanced_functions/archive_drawers.py --prefix cicindelidae_34_4_10
```

This compresses the drawer folder into `archive/cicindelidae_34_4_10.zip`
and deletes the original after verifying the zip. By default only the
original drawer image, all JSONs, and all CSVs are kept (everything else
can be regenerated by re-running the pipeline on the restored archive).

---

## 5. Per-script reference

### `master_merge.py`

**Purpose:** Aggregates per-drawer pipeline outputs into one set of master
CSVs spanning all drawers (or all drawers matching a prefix).

**Common usage:**

```
python master_merge.py                              # all drawers
python master_merge.py --prefix cicindelidae_       # filter by prefix
python master_merge.py --prefix 34_4_10 34_7_9      # multiple prefixes
```

**Inputs:** Reads from `drawers/<drawer_id>/` for every matching drawer. No
required input arguments — defaults work for the standard project layout.

**Outputs:** `master_data/master_<prefix>_<timestamp>/` containing:

- `master_specimens.csv`, `master_trays.csv`, `master_drawers.csv` — the three summary CSVs
- `master_inputs/` subfolder with per-source aggregations (taxonomy, barcodes, geocodes, localities, etc.)
- `run_log.txt` — manifest of the run

**All flags:**

| Flag | Purpose |
|---|---|
| `--drawers_dir PATH` | Override default `drawers/` location |
| `--output_dir PATH` | Override default `master_data/master` base name |
| `--prefix PREFIX [PREFIX ...]` | Filter to drawers whose names start with these strings |

**Common errors:** None typical. Missing per-drawer files are skipped with
`[SKIP]` warnings rather than crashing.

---

### `scaffold_barcodes.py`

**Purpose:** Appends new specimen rows to `curation/specimen_barcodes.csv`
so curators can fill in specimen barcode/ID # values.

**Common usage:**

```
python advanced_functions/scaffold_barcodes.py --master_dir master_data/master_<...>
python advanced_functions/scaffold_barcodes.py --master_dir <PATH> --prefix Cicindelidae
```

**Inputs:**

- `<master_dir>/master_specimens.csv` (required)
- `curation/specimen_barcodes.csv` (existing, if any — for deduplication)

**Outputs:** Appends to `curation/specimen_barcodes.csv`. Existing rows are
never touched. The first run creates the file with a header.

**The `condition` column auto-fill:** Each new row gets one of three
condition values based on pipeline data:

- `"missing mask"` — the segmentation model failed to mask this specimen
- `"bad size — review"` — measurement is anomalous (mask error or damaged specimen)
- `"intact specimen"` — neither flag tripped (the common case)

The curator can override any of these.

**All flags:**

| Flag | Purpose |
|---|---|
| `--master_dir PATH` | **Required.** Path to a `master_<timestamp>/` run folder |
| `--prefix PREFIX [PREFIX ...]` | Only include specimens whose drawer_id starts with these prefixes |
| `--rerun` | Overwrite the existing barcode file (DESTROYS curator entries; confirmation prompt before doing so) |

**Common errors:**

- `master_specimens.csv not found` — your `--master_dir` path is wrong, or you ran `master_merge.py` to a non-default location.

---

### `scaffold_locations.py`

**Purpose:** Appends new specimen rows to `curation/checked_locations.csv`
with LLM-parsed locality fields pre-populated, so curators can validate, fill
missing information, and approve for further databasing.

**Common usage:**

```
python advanced_functions/scaffold_locations.py --master_dir master_data/master_<...>
python advanced_functions/scaffold_locations.py --master_dir <PATH> --prefix Cicindelidae
```

**Inputs:**

- `<master_dir>/master_inputs/master_specimen_localities.csv` (required)
- `curation/checked_locations.csv` (existing, if any — for deduplication)

**Outputs:** Appends to `curation/checked_locations.csv`. Existing rows are
never touched. The first run creates the file with a header. Reports orphan
rows (specimens in the curation file no longer present in the latest master
run) for manual review.

**All flags:**

| Flag | Purpose |
|---|---|
| `--master_dir PATH` | **Required.** Path to a `master_<timestamp>/` run folder |
| `--prefix PREFIX [PREFIX ...]` | Only include specimens whose drawer_id starts with these prefixes |
| `--rerun` | Overwrite the existing curation file (DESTROYS approvals; confirmation prompt before doing so) |

**Common errors:**

- `master_specimen_localities.csv not found` — `master_merge.py` didn't include this file. Re-run `master_merge.py`.

---

### `emu_format.py`

**Purpose:** Produces an EMu-shaped catalog CSV from curated data.

**Common usage:**

```
python advanced_functions/emu_format.py --master_dir master_data/master_<...>
python advanced_functions/emu_format.py --master_dir <PATH> --prefix Cicindelidae
python advanced_functions/emu_format.py --master_dir <PATH> --camera macropod
```

**Inputs:**

- `<master_dir>/master_specimens.csv`
- `<master_dir>/master_inputs/master_taxonomy.csv`
- `<master_dir>/master_inputs/master_geocodes.csv`
- `curation/specimen_barcodes.csv`
- `curation/checked_locations.csv`
- `drawers/<drawer_id>/specimens/...` (recursive image search for multimedia)

**Outputs:** `advanced_outputs/emu_upload/emu_<prefix>_<timestamp>/` containing:

- `emu_catalog.csv` — the catalog with EMu field-name headers
- `emu_pending.csv` — specimens that didn't pass all gates
- `multimedia/` — renamed specimen images (`<BARCODE#>_<taxonomy>_dorsal_<camera>_ddissect.<ext>`)
- `run_log.txt`

**Strict gates:** A specimen is included in `emu_catalog.csv` only if all
three pass:

- has a non-empty `BARCODE#` in `specimen_barcodes.csv`
- has `approved=yes` in `checked_locations.csv`
- has a non-empty `full_taxonomy`

**All flags:**

| Flag | Purpose |
|---|---|
| `--master_dir PATH` | **Required.** Path to a `master_<timestamp>/` run folder |
| `--prefix PREFIX [PREFIX ...]` | Only include specimens whose drawer_id starts with these prefixes |
| `--drawers_dir PATH` | Override default `drawers/` location |
| `--camera NAME` | Camera identifier embedded in image filenames (default: `gigamacro`) |

**Common errors:**

- `No barcodes found` / `No locations found` — the curation files don't exist yet. Run the scaffolds first.
- `Images missing` warnings — the script couldn't find images for some specimens. Check that `drawers/<drawer_id>/specimens/` actually contains images named `<full_id>.<ext>`.

---

### `gbif_format.py`

**Purpose:** Produces a Darwin Core-formatted occurrence CSV ready for
upload to GBIF via IPT (Integrated Publishing Toolkit).

**Common usage:**

```
python advanced_functions/gbif_format.py --master_dir master_data/master_<...>
python advanced_functions/gbif_format.py --master_dir <PATH> --prefix Cicindelidae
```

**Inputs:** Same as `emu_format.py` (master_specimens, master_taxonomy, both
curation files).

**Outputs:** `advanced_outputs/gbif_upload/gbif_<prefix>_<timestamp>/` containing:

- `occurrence.csv` — Darwin Core occurrence records
- `gbif_pending.csv` — excluded specimens with reasons
- `run_log.txt`

**Strict gates:** Same as `emu_format.py`.

**`countryCode` auto-fill:** GBIF requires ISO 3166-1 alpha-2 country codes
(`US`, `GB`, `PL`, etc.). The script uses the `pycountry` library to derive
these from the `country` column. If `pycountry` isn't installed, you'll get a
warning at startup and the `countryCode` column will be left blank.

```
pip install pycountry
```

**Image URLs:** GBIF doesn't host images, only links to them. By default
the `associatedMedia` column is left blank. If you have a public URL pattern
for your specimen images, you can pass it with `--image_url_pattern`:

```
python advanced_functions/gbif_format.py --master_dir <PATH> \
    --image_url_pattern "https://images.fieldmuseum.org/specimens/{catalogNumber}.jpg"
```

The placeholders `{catalogNumber}` and `{full_id}` are substituted per row.

**All flags:**

| Flag | Purpose |
|---|---|
| `--master_dir PATH` | **Required.** Path to a `master_<timestamp>/` run folder |
| `--prefix PREFIX [PREFIX ...]` | Only include specimens whose drawer_id starts with these prefixes |
| `--image_url_pattern URL` | URL template with `{catalogNumber}` or `{full_id}` placeholders |

**Common errors:**

- See `emu_format.py` — same gate failures apply.

---

### `sort_specimens.py`

**Purpose:** Sort specimen images into `train/`, `valid/`, and `test/`
folders organized by taxonomy, ready for species-ID classification model
training. Uses a 70/20/10 split with edge-case handling for taxa
with very few specimens.

**Common usage:**

```
python advanced_functions/sort_specimens.py --master_dir master_data/master_<...>
python advanced_functions/sort_specimens.py --master_dir <PATH> --prefix Cicindelidae
python advanced_functions/sort_specimens.py --master_dir <PATH> --unmasked
python advanced_functions/sort_specimens.py --master_dir <PATH> --run_name my_split_v1
```

**Inputs:**

- `<master_dir>/master_specimens.csv`
- `drawers/<drawer_id>/whitebg_specimens/...` (default) or `drawers/<drawer_id>/specimens/...` (with `--unmasked`)

**Outputs:** `advanced_outputs/classification_splits/<run_name>/` containing:

- `train/<Genus_species>/<full_id>.<ext>` — 70% of each taxon
- `valid/<Genus_species>/<full_id>.<ext>` — 20%
- `test/<Genus_species>/<full_id>.<ext>` — 10%
- `manifest.csv` — one row per copied image with columns `drawer_id, full_id, filename, full_taxonomy, folder_name, split, src_path, dest_path`. Lets you trace any image back to its origin.
- `run_log.txt`

**Loose gates:** This script does NOT require `FMNH-INS#` or `approved=yes`.
Any specimen with a non-empty `full_taxonomy` and a found image is included.
This is training data, not a database upload — curator approval isn't
relevant for ML model input.

**Split edge cases:** Some taxa have very few specimens. The script handles
this rather than failing or making meaningless splits:

| Specimens (n) | train | valid | test |
|---|---|---|---|
| 1 | 1 | 0 | 0 |
| 2 | 1 | 1 | 0 |
| 3 | 2 | 1 | 0 |
| 5 | 4 | 1 | 0 |
| 10 | 7 | 2 | 1 |
| 100 | 70 | 20 | 10 |

The end-of-run summary shows a class size distribution so you can spot
training-data problems before training (e.g., "8 taxa have only 1 specimen").

**Reproducibility:** `--seed 42` (default) gives the same split every time
the script is run on the same input. Pass a different seed to re-shuffle.

**Folder names:** Same taxonomy normalization as `emu_format.py` filenames.
Subgenera dropped, subspecies kept, hybrids handled. Examples:

- `Cicindela longilabris` → `Cicindela_longilabris/`
- `Cicindela hamata monti` → `Cicindela_hamata_monti/`
- `Habroscelimorpha dorsalis x venusta` → `Habroscelimorpha_dorsalis_x_venusta/`

**All flags:**

| Flag | Purpose |
|---|---|
| `--master_dir PATH` | **Required.** Path to a `master_<timestamp>/` run folder |
| `--prefix PREFIX [PREFIX ...]` | Only include specimens whose drawer_id starts with these prefixes |
| `--drawers_dir PATH` | Override default `drawers/` location |
| `--unmasked` | Use raw `specimens/` images instead of `whitebg_specimens/` (the default) |
| `--run_name NAME` | Custom name for the output folder (default: `<prefix>_<timestamp>`) |
| `--seed N` | Random seed for reproducible splits (default: 42) |

**Common errors:**

- `Run folder already exists` — pick a different `--run_name` or delete the existing folder. Default timestamped names won't collide unless you re-run within the same minute.
- `Skipped (no image)` warnings — common if you pass `--unmasked` to a drawer where masking is the only step that ran, or vice versa. Check the `whitebg_specimens/` vs `specimens/` folder structure for the affected drawer.

---

### `archive_drawers.py`

**Purpose:** Move drawer folders into compressed zip archives to free up
disk space, or restore previously-archived drawers back into the active
`drawers/` directory.

**Common usage:**

```
# Archive (lean by default — only essentials kept)
python advanced_functions/archive_drawers.py --prefix Cicindelidae_Drawer
python advanced_functions/archive_drawers.py --all

# Restore
python advanced_functions/archive_drawers.py --restore --prefix Cicindelidae_Drawer
```

**Lean mode (default):** Only the bare minimum needed to reconstruct results
is kept in the zip. Everything else is permanently deleted along with the
source folder.

**Always kept:**

- Original drawer image (in `fullsize/`)
- All `.json` files (coordinates, mask polygons, etc.)
- All `.csv` files (transcriptions, measurements, etc.)

**Always deleted unless flagged:**

- Specimen crops (use `--keep_specimens` to retain)
- Tray crops (use `--keep_trays` to retain)
- Transparency images (use `--keep_transparencies` to retain)
- White-background specimens, labels, masks, resized images, guides — always deleted

You can rebuild any deleted images by re-running `process_images.py` on the
restored drawer (the original image + saved coordinate JSONs are sufficient).

**Confirmation prompt:** Before any destructive operation, the script shows
a per-drawer plan with before/after sizes and an explicit list of what will
be kept vs deleted. Type `yes` to proceed; anything else aborts.

**Atomic operation:** The source folder is only deleted **after** the zip
has been written and verified. If anything goes wrong during zipping, the
source remains intact and you'll find an orphaned `.zip.tmp` file in the
archive directory that's safe to delete manually.

**Restore behavior:**

- Extracts each matching zip back into `drawers/<drawer_id>/`
- Leaves the zip in place (your archive remains intact as a backup)
- Skips drawers whose folder already exists, unless `--rerun` is set

**All flags:**

| Flag | Purpose |
|---|---|
| `--prefix PREFIX [PREFIX ...]` | Select drawers/archives by prefix (mutually exclusive with `--all`) |
| `--all` | Operate on all drawers/archives (mutually exclusive with `--prefix`) |
| `--restore` | Restore mode (default is archive mode) |
| `--drawers_dir PATH` | Override default `drawers/` location |
| `--archive_dir PATH` | Override default `archive/` location |
| `--rerun` | Overwrite the destination if it already exists |
| `--keep_specimens` | Also keep `specimens/` folder |
| `--keep_trays` | Also keep `trays/` folder |
| `--keep_transparencies` | Also keep `transparencies/` folder |

**Common errors:**

- "Archive already exists" `[SKIP]` — pass `--rerun` to overwrite
- Slow zipping — image files use ZIP_STORED (no compression) since they don't compress well, but very large data files can still take time

---
