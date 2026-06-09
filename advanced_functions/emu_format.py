#!/usr/bin/env python3
"""
emu_format.py

Produce an EMu-shaped catalog CSV from DrawerDissect outputs. Column headers
match EMu field names. Reference fields like IdeTaxonRef_tab.irn are filled
with the human-readable values (taxonomy strings, collector names) that a
downstream IRN-resolution pipeline (Wei Han's R script or equivalent) is
expected to overwrite with real IRNs before EMu import.

This script's job ends at producing a clean, well-named spreadsheet. IRN
lookups, site hierarchy parenting, and EMu API calls are all out of scope.

Reads from:
    <master_dir>/master_specimens.csv
    <master_dir>/master_inputs/master_taxonomy.csv
    <master_dir>/master_inputs/master_geocodes.csv
    curation/specimen_barcodes.csv          (curator-validated catalogNumbers)
    curation/checked_locations.csv          (curator-validated localities)
    drawers/<drawer_id>/specimens/...       (recursive image search)

Writes to:
    advanced_outputs/emu_upload/emu_<prefix>_<timestamp>/
        emu_catalog.csv     EMu-shaped records, one row per specimen
        emu_pending.csv     Specimens excluded due to missing scaffolding
        multimedia/         Renamed specimen images for EMu Multimedia
        run_log.txt         Run manifest

Build gates: a specimen is included in emu_catalog.csv only if ALL pass:
    - has a non-empty FMNH-INS# in specimen_barcodes.csv
    - has approved=yes in checked_locations.csv
    - has a non-empty full_taxonomy
Otherwise it goes to emu_pending.csv with all failing reasons listed.

Notable EMu field handling:
    - LocPermanentLocationRef.irn ← unit_barcode (already an IRN; EMu generated)
    - IdeTaxonRef_tab.irn         ← full_taxonomy string (R script overwrites)
    - ColParticipantRef_tab.irn   ← recordedBy string (R script overwrites)
    - LotRegionSingleValue        ← geocode expanded to full realm name
                                    (NEA → Nearctic, etc.)

Multimedia filename convention:
    <FMNH-INS#>_<taxonomy>_dorsal_<camera>_ddissect.<ext>
    Examples:
        4832537_Cicindela_longilabris_dorsal_gigamacro_ddissect.tif
        4832555_Habroscelimorpha_dorsalis_saulcyi_x_venusta_dorsal_gigamacro_ddissect.tif

Usage:
    python advanced_functions/emu_format.py --master_dir master_<...>
    python advanced_functions/emu_format.py --master_dir <PATH> --prefix Cicindelidae
    python advanced_functions/emu_format.py --master_dir <PATH> --camera macropod
"""

import argparse
import csv
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable


# ── Constants ────────────────────────────────────────────────────────────────

CURATION_DIR = "curation"
BARCODES_FILE = "specimen_barcodes.csv"
LOCATIONS_FILE = "checked_locations.csv"
DRAWERS_DIR_DEFAULT = "drawers"
OUTPUT_BASE = Path("advanced_outputs/emu_upload")
TIMESTAMP_FMT = "%Y-%m-%d-%H-%M"

# ── EMu field mapping ────────────────────────────────────────────────────────
# Headers below are the literal EMu field names expected by EMu's CSV import.

CATALOG_COLUMNS = [
    "LotOtherNo_tab",                                # full_id
    "emultimedia.MulIdentifier",                     # renamed image filename
    "LocPermanentLocationRef.irn",                   # auto-populated from unit_barcode (EMu generated these)
    "IdeTaxonRef_tab.irn",                           # full_taxonomy text (R script overwrites with IRN)
    "irn",                                           # FMNH-INS#
    "LotRegionSingleValue",                          # geocode expanded to full realm name
    "LotRegionCountry",                              # country
    "esites.LotRegionStateProvince",                 # state/province
    "esites.LotRegionCounty",                        # county
    "esites.LotRegionCity",                          # city/municipality
    "esites.PolLocality",                            # precise location
    "esites.LocElevationASLFromMt",                  # elevation (m) from
    "esites.LocElevationASLToMt",                    # elevation (m) to
    "esites.LocElevationASLFromFt",                  # elevation (ft) from
    "esites.LocElevationASLToFt",                    # elevation (ft) to
    "esites.LatLatitudeDecimal_nesttab",             # decimal latitude
    "esites.LatLongitudeDecimal_nesttab",            # decimal longitude
    "ecollectionevents.HabHabitat",                  # habitat
    "ecollectionevents.HabMicroHabitat",             # microhabitat (currently always blank)
    "ColCollectionMethod",                           # collection method (matches boss's import format)
    "ecollectionevents.ColDateVisitedFrom",          # date visited from
    "ecollectionevents.ColDateVisitedTo",            # date visited to
    "ColParticipantRef_tab.irn",                     # recordedBy text (R script overwrites with IRN)
    "LotOtherNo_tab_other",                          # other_collect_nums (currently always blank)
    "PheSex_tab",                                    # sex (currently always blank)
    "PheStage_tab",                                  # lifestage (currently always blank)
    "ecatalogue.TasDescription_tab",                 # transcription model
]
NUM_COLUMNS = len(CATALOG_COLUMNS)  # 27

# 3-letter geocode → full realm name.
GEOCODE_TO_REALM = {
    "NEA": "Nearctic",
    "NEO": "Neotropical",
    "AUS": "Australasian",
    "PAL": "Palearctic",
    "AFR": "Afrotropical",
    "ORI": "Oriental",
    "PAC": "Oceanic",
}

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")

PENDING_COLUMNS = ["full_id", "FMNH_INS", "tray_id", "exclusion_reasons"]


# ── Helpers ──────────────────────────────────────────────────────────────────

def resolve_master_dir(master_dir_arg: str) -> Path:
    master = Path(master_dir_arg)
    if not master.is_dir():
        print(f"[ERROR] master folder not found: {master}")
        sys.exit(1)
    return master


def load_csv_dict(path: Path, key_col: str) -> dict:
    """Load a CSV into {key: row_dict}. Returns {} if file doesn't exist."""
    if not path.exists():
        return {}
    out = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            k = row.get(key_col, "")
            if k:
                out[k] = row
    return out


def parse_taxonomy_for_filename(full_taxonomy: str) -> str:
    """Build the taxonomy portion of a multimedia image filename."""
    if not full_taxonomy.strip():
        return "unknown"

    cleaned = re.sub(r"\([^)]*\)", "", full_taxonomy)
    safe = lambda s: re.sub(r"[^A-Za-z0-9]", "", s)
    parts = [safe(p) for p in cleaned.split() if safe(p)]

    if not parts:
        return "unknown"

    lower_parts = [p.lower() for p in parts]
    if "x" in lower_parts:
        x_idx = lower_parts.index("x")
        before = parts[:x_idx]
        after = parts[x_idx + 1:]
        if before and after:
            return "_".join(before) + "_x_" + after[-1]
        return "_".join(p for p in parts if p.lower() != "x")

    return "_".join(parts)


def parse_genus(full_taxonomy: str) -> str:
    """Extract just the genus from full_taxonomy, no sanitization."""
    if not full_taxonomy.strip():
        return ""
    cleaned = re.sub(r"\([^)]*\)", "", full_taxonomy).strip()
    parts = cleaned.split()
    return parts[0] if parts else ""


def parse_elevation(verbatim: str) -> dict:
    """Parse an elevation string into the four EMu columns."""
    out = {"elevation_fr": "", "elevation_to": "",
           "elevation_fr_ft": "", "elevation_to_ft": ""}
    if not verbatim or not verbatim.strip():
        return out

    s = verbatim.strip().lower().replace(" ", "")
    is_feet = s.endswith("ft") or "feet" in s or "'" in s
    is_meters = s.endswith("m") or "meters" in s or "metres" in s
    s_num = re.sub(r"(ft|feet|m|meters|metres|')$", "", s)
    s_num = s_num.replace("'", "")

    range_match = re.match(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$", s_num)
    single_match = re.match(r"^(\d+(?:\.\d+)?)$", s_num)

    if range_match:
        fr, to = range_match.group(1), range_match.group(2)
    elif single_match:
        fr, to = single_match.group(1), ""
    else:
        return out

    if is_feet:
        out["elevation_fr_ft"] = fr
        out["elevation_to_ft"] = to
    else:
        out["elevation_fr"] = fr
        out["elevation_to"] = to
    return out


def parse_event_date(event_date: str) -> tuple:
    """Split an ISO 8601-ish eventDate into (date_from, date_to)."""
    s = event_date.strip()
    if not s:
        return ("", "")
    if "/" in s:
        parts = [p.strip() for p in s.split("/", 1)]
        return (parts[0], parts[1] if len(parts) > 1 else parts[0])
    return (s, s)


def format_collectors(recorded_by_field: str) -> str:
    """Normalize a recordedBy value to use ',' as separator for multiple names."""
    s = recorded_by_field.strip()
    if not s:
        return ""
    s = re.sub(r"\s*(?:&|\band\b|\||;)\s*", ",", s, flags=re.IGNORECASE)
    s = re.sub(r",+", ",", s)
    return s.strip(", ").strip()


def make_run_folder(prefixes: list) -> Path:
    timestamp = datetime.now().strftime(TIMESTAMP_FMT)
    if prefixes:
        cleaned = [p.rstrip("_") for p in prefixes]
        prefix_part = "+".join(cleaned)
        return OUTPUT_BASE / f"emu_{prefix_part}_{timestamp}"
    return OUTPUT_BASE / f"emu_{timestamp}"


# ── Image discovery & copy ──────────────────────────────────────────────────

def find_specimen_image(drawers_dir: Path, drawer_id: str, full_id: str) -> Path | None:
    """Recursively search drawers/<drawer_id>/specimens/ for an image matching full_id."""
    specimens_root = drawers_dir / drawer_id / "specimens"
    if not specimens_root.is_dir():
        return None
    for ext in IMAGE_EXTENSIONS:
        for candidate in specimens_root.rglob(f"{full_id}.*"):
            if candidate.suffix.lower() in IMAGE_EXTENSIONS:
                return candidate
    return None


def build_image_filename(catalog_number: str, full_taxonomy: str,
                        camera: str, original_ext: str) -> str:
    """Build the EMu multimedia filename for one specimen image."""
    taxonomy_part = parse_taxonomy_for_filename(full_taxonomy)
    return f"{catalog_number}_{taxonomy_part}_dorsal_{camera}_ddissect{original_ext}"


# ── Main processing ──────────────────────────────────────────────────────────

def build_emu_row(full_id: str, master_row: dict, location_row: dict,
                  geocode: str, catalog_number: str,
                  image_filename: str) -> list:
    """Build a row using EMu field names as the column schema."""
    row = [""] * NUM_COLUMNS

    full_taxonomy = master_row.get("full_taxonomy", "")
    country = location_row.get("country", "")
    collectors = format_collectors(location_row.get("recordedBy", ""))

    elev = parse_elevation(location_row.get("verbatimElevation", ""))
    date_from, date_to = parse_event_date(location_row.get("eventDate", ""))
    region_name = GEOCODE_TO_REALM.get(geocode.strip().upper(), "")

    row[0]  = full_id                                       # LotOtherNo_tab
    row[1]  = image_filename                                # emultimedia.MulIdentifier
    row[2]  = master_row.get("unit_barcode", "")            # LocPermanentLocationRef.irn
    row[3]  = full_taxonomy                                 # IdeTaxonRef_tab.irn
    row[4]  = catalog_number                                # irn (= FMNH-INS#)

    row[5]  = region_name                                   # LotRegionSingleValue
    row[6]  = country                                       # LotRegionCountry
    row[7]  = location_row.get("stateProvince", "")
    row[8]  = location_row.get("county", "")
    row[9]  = location_row.get("municipality", "")
    row[10] = location_row.get("locality", "")

    row[11] = elev["elevation_fr"]
    row[12] = elev["elevation_to"]
    row[13] = elev["elevation_fr_ft"]
    row[14] = elev["elevation_to_ft"]

    row[15] = location_row.get("decimalLatitude", "")
    row[16] = location_row.get("decimalLongitude", "")

    row[17] = location_row.get("habitat", "")
    # row[18] HabMicroHabitat — currently always blank
    row[19] = location_row.get("samplingProtocol", "")      # ColCollectionMethod
    row[20] = date_from
    row[21] = date_to
    row[22] = collectors                                    # ColParticipantRef_tab.irn (R script overwrites)
    # row[23] other_collect_nums — blank
    # row[24] sex — blank
    # row[25] lifestage — blank
    row[26] = location_row.get("model", "")                 # transcription model

    return row


def process_specimens(master_specimens: Path, taxonomy: dict, barcodes: dict,
                      locations: dict, geocodes: dict, prefixes: list,
                      drawers_dir: Path, camera: str):
    """Iterate specimens, classify into catalog rows or pending rows."""
    catalog_rows = []
    pending_rows = []
    drawer_counts = Counter()

    with master_specimens.open(newline="") as f:
        for row in csv.DictReader(f):
            full_id = row.get("full_id", "")
            drawer_id = row.get("drawer_id", "")
            tray_id = row.get("tray_id", "")
            full_taxonomy = row.get("full_taxonomy", "")

            if not full_id:
                continue
            if prefixes and not any(drawer_id.startswith(p) for p in prefixes):
                continue

            drawer_counts[drawer_id or "?"] += 1

            # Gates
            reasons = []

            barcode_row = barcodes.get(full_id, {})
            catalog_number = barcode_row.get("FMNH-INS#", "").strip()
            if not catalog_number:
                reasons.append("no FMNH-INS#")

            location_row = locations.get(full_id)
            if location_row is None:
                reasons.append("no locality entry")
            elif location_row.get("approved", "").strip().lower() != "yes":
                reasons.append("locality not approved")

            if not full_taxonomy.strip():
                reasons.append("no scientificName")

            if reasons:
                pending_rows.append({
                    "full_id": full_id,
                    "FMNH_INS": catalog_number,
                    "tray_id": tray_id,
                    "exclusion_reasons": ", ".join(reasons),
                })
                continue

            src_image = find_specimen_image(drawers_dir, drawer_id, full_id)
            if src_image is not None:
                image_filename = build_image_filename(
                    catalog_number=catalog_number,
                    full_taxonomy=full_taxonomy,
                    camera=camera,
                    original_ext=src_image.suffix,
                )
            else:
                image_filename = ""

            geocode = geocodes.get(tray_id, {}).get("geocode", "")
            catalog_row = build_emu_row(
                full_id=full_id,
                master_row=row,
                location_row=location_row,
                geocode=geocode,
                catalog_number=catalog_number,
                image_filename=image_filename,
            )
            catalog_rows.append((full_id, full_taxonomy, catalog_number,
                                 src_image, image_filename, catalog_row))

    return catalog_rows, pending_rows, drawer_counts


# ── Output ───────────────────────────────────────────────────────────────────

def write_catalog_csv(path: Path, rows: list):
    """Write the EMu catalog CSV with header row."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CATALOG_COLUMNS)
        for entry in rows:
            writer.writerow(entry[5])


def write_pending_csv(path: Path, rows: list):
    """Write the pending CSV — has header, intended for human review."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PENDING_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def copy_multimedia(catalog_rows: list, multimedia_dir: Path) -> tuple:
    """Copy specimen images into multimedia/ using pre-resolved paths/names."""
    multimedia_dir.mkdir(parents=True, exist_ok=True)
    n_copied = 0
    missing = []

    for full_id, _full_taxonomy, _catalog_number, src, new_name, _row in tqdm(
        catalog_rows, desc="Copying images", unit="img", leave=False
    ):
        if src is None:
            missing.append(full_id)
            continue
        dest = multimedia_dir / new_name
        try:
            shutil.copy2(src, dest)
            n_copied += 1
        except Exception as e:
            print(f"  [ERROR] {full_id}: could not copy image -- {e}")
            missing.append(full_id)

    return n_copied, len(missing), missing


def write_run_log(log_path: Path, args, master_dir: Path,
                  catalog_rows: list, pending_rows: list,
                  drawer_counts: Counter, n_copied: int, n_missing: int):
    pending_reasons = Counter()
    for row in pending_rows:
        for r in row["exclusion_reasons"].split(","):
            pending_reasons[r.strip()] += 1

    command = f"python {Path(sys.argv[0]).name} " + " ".join(sys.argv[1:])
    with log_path.open("w") as f:
        f.write("DrawerDissect emu_format run\n")
        f.write("=" * 50 + "\n")
        f.write(f"Timestamp        : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Command          : {command}\n")
        f.write(f"Master input     : {master_dir}\n")
        f.write(f"Drawers dir      : {Path(args.drawers_dir).absolute()}\n")
        f.write(f"Camera           : {args.camera}\n")
        f.write(f"Prefix(es)       : {', '.join(args.prefix) if args.prefix else '(all drawers)'}\n")
        f.write(f"\nResults:\n")
        f.write(f"  Specimens scanned : {len(catalog_rows) + len(pending_rows)}\n")
        f.write(f"  Catalog rows      : {len(catalog_rows)}\n")
        f.write(f"  Pending rows      : {len(pending_rows)}\n")
        f.write(f"  Images copied     : {n_copied}\n")
        f.write(f"  Images missing    : {n_missing}\n")
        if pending_reasons:
            f.write(f"\nPending breakdown (a specimen may have multiple reasons):\n")
            for reason, n in sorted(pending_reasons.items(), key=lambda x: -x[1]):
                f.write(f"  {reason:<30} {n:>5}\n")
        if drawer_counts:
            f.write(f"\nSpecimens scanned by drawer:\n")
            for drawer, n in sorted(drawer_counts.items()):
                f.write(f"  {drawer:<40} {n:>5}\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--master_dir", metavar="PATH", required=True,
                        help="Path to the master_<timestamp>/ run folder.")
    parser.add_argument("--prefix", nargs="+", default=[],
                        help="Only include specimens whose drawer_id starts with one of these prefixes")
    parser.add_argument("--drawers_dir", default=DRAWERS_DIR_DEFAULT,
                        help=f"Active drawers directory (default: '{DRAWERS_DIR_DEFAULT}')")
    parser.add_argument("--camera", default="gigamacro",
                        help="Camera identifier to embed in image filenames (default: gigamacro)")
    args = parser.parse_args()

    # Resolve inputs
    master_dir = resolve_master_dir(args.master_dir)
    master_specimens_csv = master_dir / "master_specimens.csv"
    master_taxonomy_csv = master_dir / "master_inputs" / "master_taxonomy.csv"
    master_geocodes_csv = master_dir / "master_inputs" / "master_geocodes.csv"
    barcodes_csv = Path(CURATION_DIR) / BARCODES_FILE
    locations_csv = Path(CURATION_DIR) / LOCATIONS_FILE
    drawers_dir = Path(args.drawers_dir)

    if not master_specimens_csv.exists():
        print(f"[ERROR] master_specimens.csv not found at: {master_specimens_csv}")
        sys.exit(1)

    # Load lookup tables
    taxonomy = load_csv_dict(master_taxonomy_csv, "tray_id")
    geocodes = load_csv_dict(master_geocodes_csv, "tray_id")
    barcodes = load_csv_dict(barcodes_csv, "full_id")
    locations = load_csv_dict(locations_csv, "specimen_id")

    if not barcodes:
        print(f"[WARNING] No barcodes found at {barcodes_csv}")
        print(f"          All specimens will be in pending. Run scaffold_barcodes.py first.\n")
    if not locations:
        print(f"[WARNING] No locations found at {locations_csv}")
        print(f"          All specimens will be in pending. Run scaffold_locations.py first.\n")

    # Process
    catalog_rows, pending_rows, drawer_counts = process_specimens(
        master_specimens_csv, taxonomy, barcodes, locations, geocodes,
        args.prefix, drawers_dir, args.camera,
    )

    # Output paths
    run_folder = make_run_folder(args.prefix)
    run_folder.mkdir(parents=True, exist_ok=True)
    catalog_path = run_folder / "emu_catalog.csv"
    pending_path = run_folder / "emu_pending.csv"
    multimedia_dir = run_folder / "multimedia"
    log_path = run_folder / "run_log.txt"

    # Write CSVs
    write_catalog_csv(catalog_path, catalog_rows)
    write_pending_csv(pending_path, pending_rows)

    # Copy images
    n_copied, n_missing, missing_ids = (0, 0, [])
    if catalog_rows:
        n_copied, n_missing, missing_ids = copy_multimedia(
            catalog_rows, multimedia_dir,
        )

    # Write log
    write_run_log(log_path, args, master_dir, catalog_rows, pending_rows,
                  drawer_counts, n_copied, n_missing)

    # Summary
    pending_reasons = Counter()
    for row in pending_rows:
        for r in row["exclusion_reasons"].split(","):
            pending_reasons[r.strip()] += 1

    print(f"\n── EMu format summary ───────────────────────")
    print(f"  Master input      : {master_dir}")
    print(f"  Output folder     : {run_folder}")
    print(f"  Specimens scanned : {len(catalog_rows) + len(pending_rows)}")
    print(f"  Catalog rows      : {len(catalog_rows)}")
    print(f"  Pending rows      : {len(pending_rows)}")
    print(f"  Images copied     : {n_copied}")
    if n_missing:
        print(f"  Images missing    : {n_missing}")
        for mid in missing_ids[:5]:
            print(f"    - {mid}")
        if n_missing > 5:
            print(f"    ... and {n_missing - 5} more")
    if pending_reasons:
        print(f"\n  Pending breakdown:")
        for reason, n in sorted(pending_reasons.items(), key=lambda x: -x[1]):
            print(f"    {reason:<30} {n:>5}")


if __name__ == "__main__":
    main()
