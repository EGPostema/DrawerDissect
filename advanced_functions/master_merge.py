"""
master_merge.py
---------------
Combines outputs from every drawer's pipeline results into master CSVs.
Each run produces a timestamped output folder so runs never overwrite
each other. A run_log.txt manifest is written into each run folder.

Run folder naming (under master_data/ by default):
    master_data/master_2026-04-30-14-23/                  (no prefix)
    master_data/master_34_4_10_2026-04-30-14-23/          (one prefix)
    master_data/master_34_4_10+34_7_9_2026-04-30-14-23/   (multiple prefixes)

Three summary CSVs are written to the run folder root:
    master_specimens.csv       <- data/merged_data_*/specimens.csv
    master_trays.csv           <- data/merged_data_*/trays.csv
    master_drawers.csv         <- data/merged_data_*/drawers.csv

Per-source aggregations are written to a master_inputs/ subfolder:
    master_specimen_localities.csv    <- transcriptions/tray_context/
    master_bugcleaner_results.csv     <- transcriptions/tray_context/
    master_measurements.csv           <- measurements/
    master_taxonomy.csv               <- transcriptions/tray_labels/
    master_unit_barcodes.csv          <- transcriptions/tray_labels/
    master_geocodes.csv               <- transcriptions/tray_labels/

Usage:
    python master_merge.py                                  # all drawers
    python master_merge.py --prefix cicindelidae_           # filter by drawer prefix
    python master_merge.py --prefix 34_4_10 34_7_9          # multiple prefixes
    python master_merge.py --drawers_dir /path/to/drawers
    python master_merge.py --output_dir archive/master      # parent folder + base name
"""

import os
import sys
import glob
import argparse
from datetime import datetime
import pandas as pd


# ---------------------------------------------------------------------------
# Task registry
# Each entry defines a CSV to collect:
#   source:   "merged_data" | "direct"
#   subpath:  path within the drawer folder (for "direct") or within
#             merged_data_*/ (for "merged_data")
#   csv:      filename
#   output:   master output filename
#
# Tasks listed in DEFAULT_TASKS write to the run folder root.
# All other tasks write to <run_folder>/master_inputs/.
# ---------------------------------------------------------------------------

TASKS = {
    # default summary CSVs (from merged_data_*/)
    "specimens":    dict(source="merged_data", subpath="",                              csv="specimens.csv",           output="master_specimens.csv"),
    "trays":        dict(source="merged_data", subpath="",                              csv="trays.csv",               output="master_trays.csv"),
    "drawers":      dict(source="merged_data", subpath="",                              csv="drawers.csv",             output="master_drawers.csv"),
    # optional extras (from fixed paths within the drawer)
    "transcriptions_localities": dict(source="direct", subpath=os.path.join("transcriptions", "tray_context"),  csv="specimen_localities.csv",  output="master_specimen_localities.csv"),
    "transcriptions_bugcleaner": dict(source="direct", subpath=os.path.join("transcriptions", "tray_context"),  csv="bugcleaner_results.csv",   output="master_bugcleaner_results.csv"),
    "measurements": dict(source="direct", subpath="measurements",                       csv="measurements.csv",        output="master_measurements.csv"),
    "taxonomy":     dict(source="direct", subpath=os.path.join("transcriptions", "tray_labels"), csv="taxonomy.csv",   output="master_taxonomy.csv"),
    "barcodes":     dict(source="direct", subpath=os.path.join("transcriptions", "tray_labels"), csv="unit_barcodes.csv", output="master_unit_barcodes.csv"),
    "geocodes":     dict(source="direct", subpath=os.path.join("transcriptions", "tray_labels"), csv="geocodes.csv",   output="master_geocodes.csv"),
}

DEFAULT_TASKS = {"specimens", "trays", "drawers"}
INPUTS_SUBDIR = "master_inputs"
LOG_FILENAME = "run_log.txt"
TIMESTAMP_FMT = "%Y-%m-%d-%H-%M"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_latest_merge_folder(data_dir: str) -> str | None:
    """Return the most recent merged_data_* folder."""
    candidates = [p for p in glob.glob(os.path.join(data_dir, "merged_data_*")) if os.path.isdir(p)]
    return sorted(candidates)[-1] if candidates else None


def drawer_ids(drawers_dir: str, prefixes: list[str] | None) -> list[str]:
    """Return sorted drawer folder names, filtered by prefix if provided."""
    if not os.path.isdir(drawers_dir):
        print(f"[ERROR] drawers directory not found: {drawers_dir}")
        return []
    return [
        name for name in sorted(os.listdir(drawers_dir))
        if os.path.isdir(os.path.join(drawers_dir, name))
        and (not prefixes or any(name.startswith(p) for p in prefixes))
    ]


def make_run_folder_path(output_base: str, prefixes: list[str] | None) -> str:
    """Build a timestamped run folder path, with prefix(es) baked in if provided."""
    timestamp = datetime.now().strftime(TIMESTAMP_FMT)
    base = output_base.rstrip("/").rstrip("\\")
    if prefixes:
        cleaned = [p.rstrip("_") for p in prefixes]
        prefix_part = "+".join(cleaned)
        return f"{base}_{prefix_part}_{timestamp}"
    return f"{base}_{timestamp}"


def output_path_for(task_key: str, run_folder: str) -> str:
    """Route default summaries to run_folder/, everything else to run_folder/master_inputs/."""
    subdir = "" if task_key in DEFAULT_TASKS else INPUTS_SUBDIR
    return os.path.join(run_folder, subdir, TASKS[task_key]["output"])


def merge_and_save(frames: list[tuple[str, pd.DataFrame]], output_path: str) -> pd.DataFrame:
    """Concatenate DataFrames, deduplicate, and save."""
    if not frames:
        print(f"  No data to write for {os.path.basename(output_path)}")
        return pd.DataFrame()

    combined = pd.concat([df for _, df in frames], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates()
    if (dropped := before - len(combined)):
        print(f"  Removed {dropped} duplicate rows")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined.to_csv(output_path, index=False)
    print(f"  Saved {len(combined)} rows -> {output_path}")
    return combined


def write_run_log(log_path: str, args, tasks_to_run, drawers_processed, results):
    """Write a manifest of this run to run_log.txt."""
    command = f"python {os.path.basename(sys.argv[0])} " + " ".join(sys.argv[1:])

    with open(log_path, "w") as f:
        f.write("DrawerDissect master_merge run\n")
        f.write("=" * 50 + "\n")
        f.write(f"Timestamp    : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Command      : {command.strip()}\n")
        f.write(f"Drawers dir  : {os.path.abspath(args.drawers_dir)}\n")
        f.write(f"Output dir   : {os.path.abspath(os.path.dirname(log_path))}\n")
        f.write(f"Prefix(es)   : {', '.join(args.prefix) if args.prefix else '(all drawers)'}\n")
        f.write(f"Drawers found: {len(drawers_processed)}\n")
        f.write("\nOutputs:\n")
        for task_key in tasks_to_run:
            df = results[task_key]
            output_name = TASKS[task_key]["output"]
            rel_path = output_name if task_key in DEFAULT_TASKS else f"{INPUTS_SUBDIR}/{output_name}"
            if df.empty:
                f.write(f"  {rel_path:<55} : no data\n")
            else:
                f.write(f"  {rel_path:<55} : {len(df):,} rows, {len(df.columns)} columns\n")
        f.write("\nDrawers processed:\n")
        for d in drawers_processed:
            f.write(f"  {d}\n")


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

def collect_task(task_key: str, drawers_dir: str, prefixes: list[str] | None) -> list[tuple[str, pd.DataFrame]]:
    """Collect CSVs for a single task across all matching drawers."""
    task = TASKS[task_key]
    results = []

    for drawer_id in drawer_ids(drawers_dir, prefixes):
        drawer_path = os.path.join(drawers_dir, drawer_id)

        if task["source"] == "merged_data":
            data_dir = os.path.join(drawer_path, "data")
            if not os.path.isdir(data_dir):
                print(f"  [SKIP] {drawer_id}: no data/ folder")
                continue
            merge_folder = find_latest_merge_folder(data_dir)
            if merge_folder is None:
                print(f"  [SKIP] {drawer_id}: no merged_data_* folder in data/")
                continue
            csv_path = os.path.join(merge_folder, task["subpath"], task["csv"])
            location_label = os.path.join(os.path.basename(merge_folder), task["csv"])
        else:
            csv_path = os.path.join(drawer_path, task["subpath"], task["csv"])
            location_label = os.path.join(task["subpath"], task["csv"])

        if not os.path.isfile(csv_path):
            print(f"  [SKIP] {drawer_id}: {task['csv']} not found in {task['subpath'] or 'merged_data_*/'}")
            continue

        try:
            df = pd.read_csv(csv_path, dtype=str).fillna("")
            print(f"  [OK]   {drawer_id}: {len(df)} rows  ({location_label})")
            results.append((drawer_id, df))
        except Exception as e:
            print(f"  [ERROR] {drawer_id}: could not read {task['csv']} -- {e}")

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Merge DrawerDissect outputs into master CSVs (timestamped per run)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python master_merge.py                                # all drawers
  python master_merge.py --prefix cicindelidae_         # filter by prefix
  python master_merge.py --prefix 34_4_10 34_7_9        # multiple prefixes
        """
    )
    parser.add_argument("--drawers_dir", default="drawers",
                        help="Root drawers directory (default: 'drawers')")
    parser.add_argument("--output_dir", default="master_data/master",
                        help="Base name for the timestamped run folder "
                             "(default: 'master_data/master', producing "
                             "'master_data/master_<timestamp>/').")
    parser.add_argument("--prefix", nargs="+", metavar="PREFIX",
                        help="Only include drawers whose names start with these prefix(es)")
    args = parser.parse_args()

    # Run every task in the registry, in the order they're defined
    tasks_to_run = list(TASKS.keys())

    # Build the timestamped run folder up front; everything writes into it
    run_folder = make_run_folder_path(args.output_dir, args.prefix)
    os.makedirs(run_folder, exist_ok=True)

    # Snapshot the matching drawer list once for logging (collect_task re-derives it per call)
    drawers_processed = drawer_ids(args.drawers_dir, args.prefix)

    print(f"\n{'='*60}")
    print(f"  DrawerDissect Master Merge")
    print(f"{'='*60}")
    print(f"  Drawers dir : {os.path.abspath(args.drawers_dir)}")
    print(f"  Run folder  : {os.path.abspath(run_folder)}")
    print(f"  Prefix(es)  : {', '.join(args.prefix) if args.prefix else '(all drawers)'}")
    print(f"{'='*60}\n")

    results = {}
    for task_key in tasks_to_run:
        task = TASKS[task_key]
        print(f"Collecting {task['csv']}...")
        frames = collect_task(task_key, args.drawers_dir, args.prefix)
        print(f"\nMerging {len(frames)} {task['csv']} file(s)...")
        df = merge_and_save(frames, output_path_for(task_key, run_folder))
        results[task_key] = df
        print()

    # Write run manifest
    log_path = os.path.join(run_folder, LOG_FILENAME)
    write_run_log(log_path, args, tasks_to_run, drawers_processed, results)

    print(f"{'='*60}")
    print(f"  Master Merge Complete")
    print(f"{'='*60}")
    for task_key in tasks_to_run:
        df = results[task_key]
        output_name = TASKS[task_key]["output"]
        rel_path = output_name if task_key in DEFAULT_TASKS else f"{INPUTS_SUBDIR}/{output_name}"
        if df.empty:
            print(f"  {rel_path:<55} : no data")
        else:
            print(f"  {rel_path:<55} : {len(df):,} rows, {len(df.columns)} columns")
    print(f"  Run folder    : {os.path.abspath(run_folder)}")
    print(f"  Run log       : {os.path.abspath(log_path)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()