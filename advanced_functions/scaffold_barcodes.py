#!/usr/bin/env python3
"""
scaffold_barcodes.py

Generate a curator-editable CSV for FMNH-INS# specimen barcoding.
Reads master_specimens.csv from the master_<timestamp>/ run folder you
specify, and writes/appends to curation/specimen_barcodes.csv (a top-level
folder that holds curator-edited files, separate from regenerable pipeline
output).

Output schema:
    tray_id, spec_###, FMNH-INS#, full_id, condition, notes

Safe to re-run: by default, only adds rows for specimens whose full_id is
not already in the barcode file. Use --rerun to overwrite (loses any
curator-entered FMNH numbers — confirmation prompt before doing so).

Usage:
    python advanced_functions/scaffold_barcodes.py --master_dir master_2026-04-30-14-23
    python advanced_functions/scaffold_barcodes.py --master_dir <PATH> --prefix Cicindelidae
    python advanced_functions/scaffold_barcodes.py --master_dir <PATH> --prefix 34_4_10 34_7_9
    python advanced_functions/scaffold_barcodes.py --master_dir <PATH> --rerun
"""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

BARCODE_COLUMNS = ["tray_id", "spec_###", "FMNH-INS#", "full_id", "condition", "notes"]
DEFAULT_CONDITION = "intact specimen"
NO_MASK_CONDITION = "missing mask"
BAD_SIZE_CONDITION = "bad size — review"
CURATION_DIR = "curation"
BARCODE_FILENAME = "specimen_barcodes.csv"


def derive_condition(specimen_row: dict) -> str:
    """Set an initial condition based on pipeline flags.

    Priority: missing mask is the more fundamental issue (no measurement is
    even possible without a mask), so it's reported first. If the mask exists
    but the measurement looks wrong, that's the bad_size case.
    """
    mask_found = specimen_row.get("mask_found", "").strip().lower()
    bad_size = specimen_row.get("bad_size", "").strip().lower()

    if mask_found in ("false", "0", "no", ""):
        return NO_MASK_CONDITION
    if bad_size in ("true", "1", "yes"):
        return BAD_SIZE_CONDITION
    return DEFAULT_CONDITION


def resolve_master_dir(master_dir_arg: str) -> Path:
    """Validate the user-provided master folder path."""
    master = Path(master_dir_arg)
    if not master.is_dir():
        print(f"[ERROR] master folder not found: {master}")
        sys.exit(1)
    return master


def extract_spec_num(full_id: str) -> str:
    """Pull the zero-padded specimen number from a full_id (e.g. ..._spec_001 -> 001)."""
    if "_spec_" not in full_id:
        return ""
    return full_id.rsplit("_spec_", 1)[1]


def load_existing_ids(barcode_csv: Path) -> set:
    """Return set of full_ids already present in the barcode file."""
    if not barcode_csv.exists():
        return set()
    with barcode_csv.open(newline="") as f:
        return {row["full_id"] for row in csv.DictReader(f) if row.get("full_id")}


def build_new_rows(master_csv: Path, prefixes: list, existing_ids: set):
    """Read master_specimens.csv, return (new_rows, drawer_counts)."""
    if not master_csv.exists():
        print(f"[ERROR] master_specimens.csv not found at: {master_csv}")
        sys.exit(1)

    rows = []
    drawer_counts = Counter()
    with master_csv.open(newline="") as f:
        for row in csv.DictReader(f):
            full_id = row.get("full_id", "")
            drawer_id = row.get("drawer_id", "")
            if not full_id:
                continue
            if prefixes and not any(drawer_id.startswith(p) for p in prefixes):
                continue
            if full_id in existing_ids:
                continue
            rows.append({
                "tray_id": row.get("tray_id", ""),
                "spec_###": extract_spec_num(full_id),
                "FMNH-INS#": "",
                "full_id": full_id,
                "condition": derive_condition(row),
                "notes": "",
            })
            drawer_counts[drawer_id or "?"] += 1
    return rows, drawer_counts


def write_rows(barcode_csv: Path, rows: list, append: bool):
    """Write rows to the barcode CSV (append or overwrite).

    If `append` is True but the file doesn't exist yet, write a header anyway —
    otherwise the first run produces a headerless CSV.
    """
    barcode_csv.parent.mkdir(parents=True, exist_ok=True)
    write_header = not append or not barcode_csv.exists()
    mode = "a" if append else "w"
    with barcode_csv.open(mode, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=BARCODE_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


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
                        help="Overwrite the existing barcode file (DESTROYS curator entries)")
    args = parser.parse_args()

    master_dir = resolve_master_dir(args.master_dir)
    master_csv = master_dir / "master_specimens.csv"
    barcode_csv = Path(CURATION_DIR) / BARCODE_FILENAME

    # Safety prompt before clobbering curator work
    if args.rerun and barcode_csv.exists():
        print(f"⚠  --rerun will overwrite {barcode_csv}")
        print(f"   Any curator-entered FMNH-INS# values will be LOST.")
        if input("   Type 'yes' to proceed: ").strip().lower() != "yes":
            print("Aborted.")
            return

    existing_ids = set() if args.rerun else load_existing_ids(barcode_csv)
    new_rows, drawer_counts = build_new_rows(master_csv, args.prefix, existing_ids)

    if not new_rows:
        print(f"\nNo new specimens to scaffold.")
        print(f"  Master input : {master_csv}")
        print(f"  Barcode file : {barcode_csv}  ({len(existing_ids)} existing rows)")
        return

    write_rows(barcode_csv, new_rows, append=not args.rerun)

    # Tally flagged conditions for the summary
    condition_counts = Counter(row["condition"] for row in new_rows)

    # Summary
    print(f"\n── Scaffold summary ─────────────────────────")
    print(f"  Master input : {master_csv}")
    print(f"  Output       : {barcode_csv}")
    print(f"  Mode         : {'rerun (overwritten)' if args.rerun else 'append'}")
    print(f"  Existing rows: {len(existing_ids)}")
    print(f"  New rows     : {len(new_rows)}")
    print(f"\n  Conditions assigned (curator can override):")
    for cond, n in sorted(condition_counts.items(), key=lambda x: -x[1]):
        print(f"    {cond:<25} {n:>5}")
    print(f"\n  By drawer:")
    for drawer, n in sorted(drawer_counts.items()):
        print(f"    {drawer:<40} {n:>5}")


if __name__ == "__main__":
    main()
