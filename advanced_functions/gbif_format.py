#!/usr/bin/env python3
"""
gbif_format.py

Produce a Darwin Core occurrence CSV ready for GBIF upload via IPT.

Reads from:
    <master_dir>/master_specimens.csv
    <master_dir>/master_inputs/master_taxonomy.csv
    curation/specimen_barcodes.csv          (curator-validated catalogNumbers)
    curation/checked_locations.csv          (curator-validated localities)

Writes to:
    advanced_outputs/gbif_upload/gbif_<prefix>_<timestamp>/
        occurrence.csv      DwC occurrence records, one row per specimen
        gbif_pending.csv    Specimens excluded with reasons
        run_log.txt         Run manifest

A specimen is included in occurrence.csv only if ALL gates pass:
    - has a non-empty catalogNumber in specimen_barcodes.csv
    - has approved=yes in checked_locations.csv
    - has a non-empty full_taxonomy (scientificName)

Otherwise it goes to gbif_pending.csv with all failing reasons listed.

This script does NOT generate meta.xml or eml.xml — those are required for
a complete DwC-A package and need to be added before upload to IPT.

Usage:
    python advanced_functions/gbif_format.py --master_dir master_2026-04-30-14-23
    python advanced_functions/gbif_format.py --master_dir <PATH> --prefix Cicindelidae
    python advanced_functions/gbif_format.py --master_dir <PATH> \\
        --image_url_pattern "https://emu-api.fieldmuseum.org/media/{catalogNumber}.jpg"
"""

import argparse
import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    import pycountry
    HAS_PYCOUNTRY = True
except ImportError:
    HAS_PYCOUNTRY = False


# ── Constants ────────────────────────────────────────────────────────────────

CURATION_DIR = "curation"
BARCODES_FILE = "specimen_barcodes.csv"
LOCATIONS_FILE = "checked_locations.csv"
OUTPUT_BASE = Path("advanced_outputs/gbif_upload")
TIMESTAMP_FMT = "%Y-%m-%d-%H-%M"

# Hardcoded for an insect-only pipeline.
KINGDOM = "Animalia"
PHYLUM = "Arthropoda"
CLASS = "Insecta"
BASIS_OF_RECORD = "PreservedSpecimen"
INSTITUTION_CODE = "FMNH"
COLLECTION_CODE = "Insects"

# Output column order — Darwin Core terms in a logical reading order.
OCCURRENCE_COLUMNS = [
    # Identity
    "occurrenceID", "catalogNumber", "basisOfRecord",
    "institutionCode", "collectionCode",
    # Taxonomy
    "scientificName", "scientificNameAuthorship",
    "kingdom", "phylum", "class",
    # Geography
    "country", "countryCode", "stateProvince", "county", "municipality",
    "verbatimLocality", "locality", "waterBody", "islandGroup", "island",
    # Collection event
    "verbatimElevation", "habitat", "samplingProtocol", "recordedBy",
    "verbatimEventDate", "eventDate", "identifiedBy", "verbatimCoordinates",
    # Media
    "associatedMedia",
]

PENDING_COLUMNS = ["full_id", "catalogNumber", "tray_id", "exclusion_reasons"]


# ── Helpers ──────────────────────────────────────────────────────────────────

def resolve_master_dir(master_dir_arg: str) -> Path:
    master = Path(master_dir_arg)
    if not master.is_dir():
        print(f"[ERROR] master folder not found: {master}")
        sys.exit(1)
    return master


def lookup_country_code(country_name: str) -> str:
    """Return ISO 3166-1 alpha-2 code, or '' if no match."""
    if not HAS_PYCOUNTRY or not country_name.strip():
        return ""
    try:
        matches = pycountry.countries.search_fuzzy(country_name)
        return matches[0].alpha_2 if matches else ""
    except Exception:
        return ""


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


def build_image_url(pattern: str, full_id: str, catalog_number: str) -> str:
    """Substitute {full_id} and/or {catalogNumber} into a URL pattern."""
    if not pattern:
        return ""
    return pattern.replace("{full_id}", full_id).replace("{catalogNumber}", catalog_number)


def make_run_folder(prefixes: list) -> Path:
    timestamp = datetime.now().strftime(TIMESTAMP_FMT)
    if prefixes:
        cleaned = [p.rstrip("_") for p in prefixes]
        prefix_part = "+".join(cleaned)
        return OUTPUT_BASE / f"gbif_{prefix_part}_{timestamp}"
    return OUTPUT_BASE / f"gbif_{timestamp}"


# ── Main processing ──────────────────────────────────────────────────────────

def process_specimens(master_specimens: Path, taxonomy: dict, barcodes: dict,
                      locations: dict, prefixes: list, image_pattern: str):
    """Iterate specimens, classify into occurrence rows or pending rows."""
    occurrence_rows = []
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

            # Check all gates and collect failure reasons
            reasons = []

            barcode_row = barcodes.get(full_id, {})
            catalog_number = barcode_row.get("FMNH-INS#", "").strip()
            if not catalog_number:
                reasons.append("no catalogNumber")

            location_row = locations.get(full_id)
            if location_row is None:
                reasons.append("no locality entry")
            elif location_row.get("approved", "").strip().lower() != "yes":
                reasons.append("locality not approved")

            if not full_taxonomy.strip():
                reasons.append("no scientificName")

            # If any gate failed, route to pending
            if reasons:
                pending_rows.append({
                    "full_id": full_id,
                    "catalogNumber": catalog_number,
                    "tray_id": tray_id,
                    "exclusion_reasons": ", ".join(reasons),
                })
                continue

            # All gates passed — build occurrence row
            tax_row = taxonomy.get(tray_id, {})
            country = location_row.get("country", "")

            occurrence_rows.append({
                # Identity
                "occurrenceID": catalog_number,
                "catalogNumber": catalog_number,
                "basisOfRecord": BASIS_OF_RECORD,
                "institutionCode": INSTITUTION_CODE,
                "collectionCode": COLLECTION_CODE,
                # Taxonomy
                "scientificName": full_taxonomy,
                "scientificNameAuthorship": tax_row.get("authority", ""),
                "kingdom": KINGDOM,
                "phylum": PHYLUM,
                "class": CLASS,
                # Geography
                "country": country,
                "countryCode": lookup_country_code(country),
                "stateProvince": location_row.get("stateProvince", ""),
                "county": location_row.get("county", ""),
                "municipality": location_row.get("municipality", ""),
                "verbatimLocality": location_row.get("verbatimLocality", ""),
                "locality": location_row.get("locality", ""),
                "waterBody": location_row.get("waterBody", ""),
                "islandGroup": location_row.get("islandGroup", ""),
                "island": location_row.get("island", ""),
                # Collection event
                "verbatimElevation": location_row.get("verbatimElevation", ""),
                "habitat": location_row.get("habitat", ""),
                "samplingProtocol": location_row.get("samplingProtocol", ""),
                "recordedBy": location_row.get("recordedBy", ""),
                "verbatimEventDate": location_row.get("verbatimEventDate", ""),
                "eventDate": location_row.get("eventDate", ""),
                "identifiedBy": location_row.get("identifiedBy", ""),
                "verbatimCoordinates": location_row.get("verbatimCoordinates", ""),
                # Media
                "associatedMedia": build_image_url(image_pattern, full_id, catalog_number),
            })

    return occurrence_rows, pending_rows, drawer_counts


# ── Output ───────────────────────────────────────────────────────────────────

def write_csv(path: Path, rows: list, columns: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_run_log(log_path: str, args, master_dir: Path, occurrence_rows: list,
                  pending_rows: list, drawer_counts: Counter, image_pattern: str):
    pending_reasons = Counter()
    for row in pending_rows:
        for r in row["exclusion_reasons"].split(","):
            pending_reasons[r.strip()] += 1

    command = f"python {Path(sys.argv[0]).name} " + " ".join(sys.argv[1:])
    with open(log_path, "w") as f:
        f.write("DrawerDissect gbif_format run\n")
        f.write("=" * 50 + "\n")
        f.write(f"Timestamp        : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Command          : {command}\n")
        f.write(f"Master input     : {master_dir}\n")
        f.write(f"Prefix(es)       : {', '.join(args.prefix) if args.prefix else '(all drawers)'}\n")
        f.write(f"Image URL pattern: {image_pattern or '(none — associatedMedia will be empty)'}\n")
        f.write(f"\nResults:\n")
        f.write(f"  Specimens scanned : {len(occurrence_rows) + len(pending_rows)}\n")
        f.write(f"  Occurrence rows   : {len(occurrence_rows)}\n")
        f.write(f"  Pending rows      : {len(pending_rows)}\n")
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
                        help="Path to the master_<timestamp>/ run folder to use as input")
    parser.add_argument("--prefix", nargs="+", default=[],
                        help="Only include specimens whose drawer_id starts with one of these prefixes")
    parser.add_argument("--image_url_pattern", default="",
                        help="URL template for specimen images, with {catalogNumber} or "
                             "{full_id} as placeholders. Leave blank to omit image URLs.")
    args = parser.parse_args()

    if not HAS_PYCOUNTRY:
        print("[WARNING] pycountry not installed — countryCode will be left blank.")
        print("          Install with: pip install pycountry\n")

    # Resolve inputs
    master_dir = resolve_master_dir(args.master_dir)
    master_specimens_csv = master_dir / "master_specimens.csv"
    master_taxonomy_csv = master_dir / "master_inputs" / "master_taxonomy.csv"
    barcodes_csv = Path(CURATION_DIR) / BARCODES_FILE
    locations_csv = Path(CURATION_DIR) / LOCATIONS_FILE

    if not master_specimens_csv.exists():
        print(f"[ERROR] master_specimens.csv not found at: {master_specimens_csv}")
        sys.exit(1)

    # Load lookup tables
    taxonomy = load_csv_dict(master_taxonomy_csv, "tray_id")
    barcodes = load_csv_dict(barcodes_csv, "full_id")
    locations = load_csv_dict(locations_csv, "specimen_id")

    if not barcodes:
        print(f"[WARNING] No barcodes found at {barcodes_csv}")
        print(f"          All specimens will be in pending. Run scaffold_barcodes.py first.\n")
    if not locations:
        print(f"[WARNING] No locations found at {locations_csv}")
        print(f"          All specimens will be in pending. Run scaffold_locations.py first.\n")

    # Process
    occurrence_rows, pending_rows, drawer_counts = process_specimens(
        master_specimens_csv, taxonomy, barcodes, locations,
        args.prefix, args.image_url_pattern,
    )

    # Write outputs
    run_folder = make_run_folder(args.prefix)
    run_folder.mkdir(parents=True, exist_ok=True)
    occurrence_path = run_folder / "occurrence.csv"
    pending_path = run_folder / "gbif_pending.csv"
    log_path = run_folder / "run_log.txt"

    write_csv(occurrence_path, occurrence_rows, OCCURRENCE_COLUMNS)
    write_csv(pending_path, pending_rows, PENDING_COLUMNS)
    write_run_log(log_path, args, master_dir, occurrence_rows, pending_rows,
                  drawer_counts, args.image_url_pattern)

    # Summary
    pending_reasons = Counter()
    for row in pending_rows:
        for r in row["exclusion_reasons"].split(","):
            pending_reasons[r.strip()] += 1

    print(f"\n── GBIF format summary ──────────────────────")
    print(f"  Master input      : {master_dir}")
    print(f"  Output folder     : {run_folder}")
    print(f"  Specimens scanned : {len(occurrence_rows) + len(pending_rows)}")
    print(f"  Occurrence rows   : {len(occurrence_rows)}")
    print(f"  Pending rows      : {len(pending_rows)}")
    if pending_reasons:
        print(f"\n  Pending breakdown:")
        for reason, n in sorted(pending_reasons.items(), key=lambda x: -x[1]):
            print(f"    {reason:<30} {n:>5}")
    print(f"\n  ⚠  occurrence.csv is not yet a complete DwC-A.")
    print(f"     A meta.xml descriptor and eml.xml dataset metadata file are")
    print(f"     required before uploading to IPT. These are not yet generated.")


if __name__ == "__main__":
    main()
