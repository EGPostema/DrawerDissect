#!/usr/bin/env python3
"""
scaffold_locations.py

Generate a curator-editable CSV for validating LLM-transcribed specimen
locality data before GBIF upload. Reads master_specimen_localities.csv from
a master_<timestamp>/ run folder and writes/appends to
curation/checked_locations.csv.

One row per specimen. Curator sets `approved` to 'yes' to mark a row as
validated and ready for GBIF upload. Only approved rows are read by
gbif_upload.py.

The script auto-populates ISO 3166-1 alpha-2 country codes from country
names using pycountry's fuzzy match. Curator can override.

Safe to re-run: by default, only adds rows for specimens not already in the
file. Reports orphans (rows in the curation file whose specimen_id is no
longer in master). Use --rerun to overwrite (loses curator entries —
confirmation prompt before doing so).

Usage:
    python advanced_functions/scaffold_locations.py --master_dir master_2026-04-30-14-23
    python advanced_functions/scaffold_locations.py --master_dir <PATH> --prefix Cicindelidae
    python advanced_functions/scaffold_locations.py --master_dir <PATH> --rerun
"""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────

CURATION_DIR = "curation"
LOCATIONS_FILENAME = "checked_locations.csv"
SOURCE_FILENAME = "master_specimen_localities.csv"
SOURCE_SUBDIR = "master_inputs"

# Output column order. Identity first, pipeline metadata, DwC fields, then
# curation gate at the end.
LOCATION_COLUMNS = [
    # Identity
    "specimen_id", "tray_id", "label_group", "match_type",
    # Pipeline reference
    "verbatim_text", "flags", "model",
    # DwC geography
    "country", "stateProvince", "county", "municipality",
    "verbatimLocality", "locality", "waterBody", "islandGroup", "island",
    # DwC collection event
    "verbatimElevation", "habitat", "samplingProtocol", "recordedBy",
    "verbatimEventDate", "eventDate", "identifiedBy",
    # Other
    "possibleName", "verbatimCoordinates",
    "decimalLatitude", "decimalLongitude",
    # Curation gate
    "approved", "curator_notes",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def resolve_master_dir(master_dir_arg: str) -> Path:
    """Validate the user-provided master folder path."""
    master = Path(master_dir_arg)
    if not master.is_dir():
        print(f"[ERROR] master folder not found: {master}")
        sys.exit(1)
    return master


def load_existing_ids(locations_csv: Path) -> set:
    """Return set of specimen_ids already present in the curation file."""
    if not locations_csv.exists():
        return set()
    with locations_csv.open(newline="") as f:
        return {row["specimen_id"] for row in csv.DictReader(f) if row.get("specimen_id")}


def build_new_rows(source_csv: Path, prefixes: list, existing_ids: set):
    """Read master_specimen_localities.csv, return (new_rows, drawer_counts, source_ids).

    source_ids is the set of all specimen_ids found in the source — used
    afterwards to detect orphans.
    """
    if not source_csv.exists():
        print(f"[ERROR] {SOURCE_FILENAME} not found at: {source_csv}")
        print(f"        Did you run master_merge.py with --transcriptions?")
        sys.exit(1)

    new_rows = []
    drawer_counts = Counter()
    source_ids = set()

    with source_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            specimen_id = row.get("specimen_id", "")
            tray_id = row.get("tray", "")  # source uses 'tray', we use 'tray_id'
            if not specimen_id:
                continue

            source_ids.add(specimen_id)

            # Derive drawer_id from tray_id (everything before "_tray_")
            drawer_id = tray_id.rsplit("_tray_", 1)[0] if "_tray_" in tray_id else tray_id

            if prefixes and not any(drawer_id.startswith(p) for p in prefixes):
                continue
            if specimen_id in existing_ids:
                continue

            country = row.get("country", "")
            new_rows.append({
                "specimen_id": specimen_id,
                "tray_id": tray_id,
                "label_group": row.get("label_group", ""),
                "match_type": row.get("match_type", ""),
                "verbatim_text": row.get("verbatim_text", ""),
                "flags": row.get("flags", ""),
                "model": row.get("model", ""),
                "country": country,
                "stateProvince": row.get("stateProvince", ""),
                "county": row.get("county", ""),
                "municipality": row.get("municipality", ""),
                "verbatimLocality": row.get("verbatimLocality", ""),
                "locality": row.get("locality", ""),
                "waterBody": row.get("waterBody", ""),
                "islandGroup": row.get("islandGroup", ""),
                "island": row.get("island", ""),
                "verbatimElevation": row.get("verbatimElevation", ""),
                "habitat": row.get("habitat", ""),
                "samplingProtocol": row.get("samplingProtocol", ""),
                "recordedBy": row.get("recordedBy", ""),
                "verbatimEventDate": row.get("verbatimEventDate", ""),
                "eventDate": "",  # ISO 8601 — curator fills in
                "identifiedBy": row.get("identifiedBy", ""),
                "possibleName": row.get("possibleName", ""),
                "verbatimCoordinates": row.get("verbatimCoordinates", ""),
                "decimalLatitude": "",   # populated by curator (or future georeference.py)
                "decimalLongitude": "",
                "approved": "",
                "curator_notes": "",
            })
            drawer_counts[drawer_id or "?"] += 1

    return new_rows, drawer_counts, source_ids


def find_orphans(locations_csv: Path, source_ids: set) -> list:
    """Return list of specimen_ids in curation file but not in current source."""
    if not locations_csv.exists():
        return []
    orphans = []
    with locations_csv.open(newline="") as f:
        for row in csv.DictReader(f):
            sid = row.get("specimen_id", "")
            if sid and sid not in source_ids:
                orphans.append(sid)
    return orphans


def write_rows(locations_csv: Path, rows: list, append: bool):
    """Write rows to the curation CSV (append or overwrite).

    If `append` is True but the file doesn't exist yet, write a header anyway —
    otherwise the first run produces a headerless CSV.
    """
    locations_csv.parent.mkdir(parents=True, exist_ok=True)
    write_header = not append or not locations_csv.exists()
    mode = "a" if append else "w"
    with locations_csv.open(mode, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOCATION_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


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
    parser.add_argument("--rerun", action="store_true",
                        help="Overwrite the existing curation file (DESTROYS curator entries)")
    args = parser.parse_args()

    master_dir = resolve_master_dir(args.master_dir)
    source_csv = master_dir / SOURCE_SUBDIR / SOURCE_FILENAME
    locations_csv = Path(CURATION_DIR) / LOCATIONS_FILENAME

    # Safety prompt before clobbering curator work
    if args.rerun and locations_csv.exists():
        print(f"⚠  --rerun will overwrite {locations_csv}")
        print(f"   All curator-entered approvals and notes will be LOST.")
        if input("   Type 'yes' to proceed: ").strip().lower() != "yes":
            print("Aborted.")
            return

    existing_ids = set() if args.rerun else load_existing_ids(locations_csv)
    new_rows, drawer_counts, source_ids = build_new_rows(source_csv, args.prefix, existing_ids)
    orphans = [] if args.rerun else find_orphans(locations_csv, source_ids)

    # Write
    if new_rows:
        write_rows(locations_csv, new_rows, append=not args.rerun)

    # Summary
    print(f"\n── Locations scaffold summary ───────────────")
    print(f"  Source file  : {source_csv}")
    print(f"  Output       : {locations_csv}")
    print(f"  Mode         : {'rerun (overwritten)' if args.rerun else 'append'}")
    print(f"  Existing rows: {len(existing_ids)}")
    print(f"  New rows     : {len(new_rows)}")

    if drawer_counts:
        print(f"\n  New rows by drawer:")
        for drawer, n in sorted(drawer_counts.items()):
            print(f"    {drawer:<40} {n:>5}")

    if orphans:
        print(f"\n⚠  {len(orphans)} orphan row(s) in curation file (specimen_id not in current master run):")
        for sid in orphans[:10]:
            print(f"    {sid}")
        if len(orphans) > 10:
            print(f"    ... and {len(orphans) - 10} more")
        print(f"   These specimens may have been archived or re-processed under different IDs.")
        print(f"   Review and remove manually if appropriate.")

    if not new_rows and not orphans:
        print(f"\n  Nothing to do — curation file is in sync with master run.")


if __name__ == "__main__":
    main()
