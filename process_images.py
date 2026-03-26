import os
import time
import argparse
import shutil
import csv
from datetime import datetime
from config import DrawerDissectConfig
from logging_utils import log, StepTimer
from functions.model_runner import build_model_runner
from functions.drawer_management import (
    get_drawers_to_process, validate_drawer_structure,
    discover_and_sort_drawers, is_specimen_only_drawer,
)
from functions.resize_drawer import resize_drawer_images
from functions.infer_drawers import infer_drawers
from functions.crop_trays import crop_trays_from_fullsize
from functions.resize_trays import resize_tray_images
from functions.infer_labels import infer_tray_labels
from functions.crop_labels import crop_labels
from functions.infer_trays import infer_tray_images
from functions.crop_specimens import crop_specimens_from_trays
from functions.specimen_guide import create_specimen_guides
from functions.infer_beetles import infer_beetles
from functions.create_masks import create_masks
from functions.multipolygon_fixer import fix_mask
from functions.measure import generate_csv_with_measurements
from functions.censor_background import censor_background
from functions.infer_pins import infer_pins
from functions.create_pinmask import create_pinmask
from functions.create_transparency import create_transparency
from functions.ocr_header import process_image_folder
from functions.ocr_specimenlabels import process_tray_context
from functions.merge_data import merge_data


def _model_param(args_val, config, model_key: str, param: str, default: float = 50) -> float:
    """
    Return the effective value for a model parameter (confidence or overlap).
    Priority: CLI argument > config.yaml value > hard default.
    """
    if args_val is not None:
        return args_val
    if config.deployment == "roboflow":
        return config.roboflow_models[model_key].get(param, default)
    return default


def run_step_for_drawer(step, config, drawer_id, args):
    """Run a single pipeline step for a single drawer."""
    with StepTimer(f"{step}_{drawer_id}"):
        mem = config.get_memory_config(step)
        sequential = args.sequential if args.sequential is not None else mem.get("sequential", False)
        max_workers = args.max_workers if args.max_workers is not None else mem.get("max_workers")
        batch_size  = args.batch_size  if args.batch_size  is not None else mem.get("batch_size")

        if sequential or max_workers is not None or batch_size is not None:
            log(f"Memory settings: sequential={sequential}, max_workers={max_workers}, batch_size={batch_size}")

        d = drawer_id

        if step == "resize_drawers":
            resize_drawer_images(
                config.get_drawer_directory(d, "fullsize"),
                config.get_drawer_directory(d, "resized"),
                sequential=sequential, max_workers=max_workers, batch_size=batch_size,
            )

        elif step == "find_trays":
            infer_drawers(
                config.get_drawer_directory(d, "resized"),
                config.get_drawer_directory(d, "coordinates"),
                build_model_runner(config, "drawer"),
                confidence=_model_param(args.drawer_confidence, config, "drawer", "confidence"),
                overlap=_model_param(args.drawer_overlap, config, "drawer", "overlap"),
            )

        elif step == "crop_trays":
            crop_trays_from_fullsize(
                config.get_drawer_directory(d, "fullsize"),
                config.get_drawer_directory(d, "resized"),
                config.get_drawer_directory(d, "trays"),
                sequential=sequential, max_workers=max_workers, batch_size=batch_size,
            )

        elif step == "resize_trays":
            resize_tray_images(
                config.get_drawer_directory(d, "trays"),
                config.get_drawer_directory(d, "resized_trays"),
            )

        elif step == "find_traylabels":
            infer_tray_labels(
                config.get_drawer_directory(d, "resized_trays"),
                config.get_drawer_directory(d, "label_coordinates"),
                build_model_runner(config, "label"),
                confidence=_model_param(args.label_confidence, config, "label", "confidence"),
                overlap=_model_param(args.label_overlap, config, "label", "overlap"),
            )

        elif step == "crop_labels":
            crop_labels(
                config.get_drawer_directory(d, "trays"),
                config.get_drawer_directory(d, "resized_trays"),
                config.get_drawer_directory(d, "label_coordinates"),
                config.get_drawer_directory(d, "labels"),
            )

        elif step == "find_specimens":
            infer_tray_images(
                config.get_drawer_directory(d, "resized_trays"),
                config.get_drawer_directory(d, "resized_trays_coordinates"),
                build_model_runner(config, "tray"),
                confidence=_model_param(args.tray_confidence, config, "tray", "confidence"),
                overlap=_model_param(args.tray_overlap, config, "tray", "overlap"),
            )

        elif step == "crop_specimens":
            crop_specimens_from_trays(
                config.get_drawer_directory(d, "trays"),
                config.get_drawer_directory(d, "resized_trays"),
                config.get_drawer_directory(d, "specimens"),
            )

        elif step == "create_traymaps":
            create_specimen_guides(
                config.get_drawer_directory(d, "resized_trays"),
                config.get_drawer_directory(d, "guides"),
            )

        elif step == "outline_specimens":
            infer_beetles(
                config.get_drawer_directory(d, "specimens"),
                config.get_drawer_directory(d, "mask_coordinates"),
                build_model_runner(config, "mask"),
                confidence=_model_param(args.beetle_confidence, config, "mask", "confidence"),
                sequential=sequential, max_workers=max_workers,
            )

        elif step == "create_masks":
            create_masks(
                config.get_drawer_directory(d, "mask_coordinates"),
                config.get_drawer_directory(d, "mask_png"),
            )

        elif step == "fix_masks":
            fix_mask(config.get_drawer_directory(d, "mask_png"))

        elif step == "measure_specimens":
            generate_csv_with_measurements(
                config.get_drawer_directory(d, "mask_png"),
                config.get_drawer_directory(d, "measurements"),
                visualization_mode=config.processing_flags.get("measurement_visualizations", "on"),
            )

        elif step == "censor_background":
            censor_background(
                config.get_drawer_directory(d, "specimens"),
                config.get_drawer_directory(d, "mask_png"),
                config.get_drawer_directory(d, "no_background"),
            )

        elif step == "outline_pins":
            infer_pins(
                config.get_drawer_directory(d, "no_background"),
                config.get_drawer_directory(d, "pin_coordinates"),
                os.path.join(config.get_drawer_directory(d, "measurements"), "measurements.csv"),
                build_model_runner(config, "pin"),
                confidence=_model_param(args.pin_confidence, config, "pin", "confidence"),
                sequential=sequential, max_workers=max_workers,
            )

        elif step == "create_pinmask":
            create_pinmask(
                config.get_drawer_directory(d, "mask_png"),
                config.get_drawer_directory(d, "pin_coordinates"),
                config.get_drawer_directory(d, "full_masks"),
            )

        elif step == "create_transparency":
            create_transparency(
                config.get_drawer_directory(d, "no_background"),
                config.get_drawer_directory(d, "full_masks"),
                config.get_drawer_directory(d, "transparencies"),
                config.get_drawer_directory(d, "whitebg_specimens"),
                sequential=sequential, max_workers=max_workers, batch_size=batch_size,
            )

        elif step in ("transcribe_barcodes", "transcribe_geocodes", "transcribe_taxonomy"):
            flag_key, csv_name, default_on = {
                "transcribe_barcodes": ("transcribe_barcodes", "unit_barcodes.csv", False),
                "transcribe_geocodes": ("transcribe_geocodes", "geocodes.csv",      False),
                "transcribe_taxonomy": ("transcribe_taxonomy", "taxonomy.csv",       True),
            }[step]

            if config.processing_flags.get(flag_key, default_on):
                import asyncio
                tray_level_dir = config.get_drawer_directory(d, "tray_level")
                os.makedirs(tray_level_dir, exist_ok=True)
                output_csv = os.path.join(tray_level_dir, csv_name)

                # ocr_header determines barcode/geocode/taxonomy mode from the csv filename
                prompt_key = {
                    "transcribe_barcodes": "barcode",
                    "transcribe_geocodes": "geocode",
                    "transcribe_taxonomy": "taxonomy",
                }[step]

                asyncio.run(process_image_folder(
                    folder_path=config.get_drawer_directory(d, "labels"),
                    output_csv=output_csv,
                    api_key=config.api_keys["anthropic"],
                    prompts=config.prompts.get(prompt_key, {}),
                    model_config=config.claude_config,
                ))
            else:
                log(f"{step} skipped (disabled in config)")

        elif step == "transcribe_specimens":
            if config.processing_flags.get("transcribe_specimens", False):
                tray_level_path = config.get_drawer_directory(d, "tray_level")
                tray_level_dir = tray_level_path if os.path.exists(tray_level_path) else None

                process_tray_context(
                    specimens_dir=config.get_drawer_directory(d, "specimens"),
                    resized_trays_coords_dir=config.get_drawer_directory(d, "resized_trays_coordinates"),
                    trays_dir=config.get_drawer_directory(d, "trays"),
                    resized_trays_dir=config.get_drawer_directory(d, "resized_trays"),
                    guides_dir=config.get_drawer_directory(d, "guides"),
                    output_dir=config.get_drawer_directory(d, "tray_context"),
                    config=config,
                    tray_level_dir=tray_level_dir,
                )
            else:
                log("transcribe_specimens skipped (disabled in config)")

        elif step == "merge_data":
            def _p(subdir, filename):
                path = os.path.join(config.get_drawer_directory(d, subdir), filename)
                return path if os.path.exists(path) else None

            merge_data(
                specimens_dir=config.get_drawer_directory(d, "specimens"),
                measurements_path=_p("measurements", "measurements.csv"),
                specimen_localities_path=_p("tray_context", "specimen_localities.csv"),
                taxonomy_path=_p("tray_level", "taxonomy.csv"),
                unit_barcodes_path=_p("tray_level", "unit_barcodes.csv"),
                geocodes_path=_p("tray_level", "geocodes.csv"),
                sizeratios_path=_p("fullsize", "sizeratios.csv"),
                labels_dir=config.get_drawer_directory(d, "labels")
                    if os.path.exists(config.get_drawer_directory(d, "labels")) else None,
                output_base_path=os.path.join(config.get_drawer_directory(d, "data"), "merged_data"),
            )


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

ALL_STEPS = [
    "resize_drawers", "find_trays", "crop_trays",
    "resize_trays", "find_traylabels", "crop_labels", "find_specimens",
    "crop_specimens", "create_traymaps", "outline_specimens", "create_masks",
    "fix_masks", "measure_specimens", "censor_background", "outline_pins",
    "create_pinmask", "create_transparency",
    "transcribe_barcodes", "transcribe_geocodes", "transcribe_taxonomy",
    "transcribe_specimens", "merge_data",
]

SPECIMEN_ONLY_STEPS = {
    "outline_specimens", "create_masks", "fix_masks", "measure_specimens",
    "censor_background", "outline_pins", "create_pinmask", "create_transparency",
    "merge_data",
}


def parse_arguments():
    parser = argparse.ArgumentParser(description="Process drawer images")
    parser.add_argument("steps", nargs="*", help="Steps to run (or 'all')")
    parser.add_argument("--from", dest="from_step", choices=ALL_STEPS,
                        help="Run from this step to the end (or --until)")
    parser.add_argument("--until", dest="until_step", choices=ALL_STEPS,
                        help="Run all steps up to and including this step")

    drawer_group = parser.add_argument_group("Drawer Selection")
    drawer_group.add_argument("--drawers", type=str,
                              help="Comma-separated drawer IDs (e.g. drawer_01,drawer_03)")
    drawer_group.add_argument("--list-drawers", action="store_true",
                              help="List available drawers and exit")
    drawer_group.add_argument("--status", action="store_true",
                              help="Show status report and exit")
    drawer_group.add_argument("--write-report", action="store_true",
                              help="Write CSV status report to status_reports/")

    proc_group = parser.add_argument_group("Processing Options")
    proc_group.add_argument("--rerun", action="store_true",
                            help="Overwrite existing outputs (requires confirmation)")

    mem_group = parser.add_argument_group("Memory Management")
    seq_group = mem_group.add_mutually_exclusive_group()
    seq_group.add_argument("--sequential", action="store_true", dest="sequential",
                           help="Process images one at a time")
    seq_group.add_argument("--parallel", action="store_false", dest="sequential",
                           help="Process images in parallel (default)")
    mem_group.add_argument("--max-workers", type=int)
    mem_group.add_argument("--batch-size", type=int)
    parser.set_defaults(sequential=None)

    model_group = parser.add_argument_group("Model Parameters")
    for model in ["drawer", "tray", "label", "beetle", "pin"]:
        model_group.add_argument(f"--{model}_confidence", type=float)
        if model not in ["beetle", "pin"]:
            model_group.add_argument(f"--{model}_overlap", type=float)

    return parser.parse_args()


def determine_steps(args):
    """Resolve the ordered list of steps to run from CLI arguments."""
    valid = ALL_STEPS + ["all"]

    if args.steps:
        invalid = [s for s in args.steps if s not in valid]
        if invalid:
            raise ValueError(f"Invalid steps: {', '.join(invalid)}. Choose from: {', '.join(valid)}")

    from_idx  = ALL_STEPS.index(args.from_step)  if args.from_step  else 0
    until_idx = ALL_STEPS.index(args.until_step) + 1 if args.until_step else len(ALL_STEPS)
    step_range = ALL_STEPS[from_idx:until_idx]

    if not args.steps or "all" in args.steps:
        return step_range

    result = list(args.steps)
    if args.from_step or args.until_step:
        result.extend(s for s in step_range if s not in result)
    return result


def confirm_rerun(steps_to_run, drawers):
    print(f"\n{'='*60}\nRERUN CONFIRMATION\n{'='*60}")
    print(f"  Steps:   {', '.join(steps_to_run)}")
    print(f"  Drawers: {', '.join(drawers)}")
    print(f"{'='*60}")
    while True:
        r = input("Continue? (y/n): ").strip().lower()
        if r in ("y", "yes"):
            return True
        if r in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'")


def clear_existing_outputs(config, drawer_id, steps_to_run):
    """Delete output files for the given steps so they will be regenerated."""
    step_clear_mapping = {
        "resize_drawers":         ["resized"],
        "find_trays":             ["coordinates"],
        "crop_trays":             ["trays"],
        "resize_trays":           ["resized_trays"],
        "find_traylabels":        ["label_coordinates"],
        "crop_labels":            ["labels"],
        "find_specimens":         ["resized_trays_coordinates"],
        "crop_specimens":         ["specimens"],
        "create_traymaps":        ["guides"],
        "outline_specimens":      ["mask_coordinates"],
        "create_masks":           ["mask_png"],
        "fix_masks":              [],
        "measure_specimens":      ["measurements"],
        "censor_background":      ["no_background"],
        "outline_pins":           ["pin_coordinates"],
        "create_pinmask":         ["full_masks"],
        "create_transparency":    ["transparencies", "whitebg_specimens"],
        "transcribe_barcodes":    ["tray_level"],
        "transcribe_geocodes":    [],
        "transcribe_taxonomy":    [],
        "transcribe_specimens": ["tray_context"],
        "merge_data":             ["data"],
    }

    cleared = []
    for step in steps_to_run:
        for dir_key in step_clear_mapping.get(step, []):
            try:
                path = config.get_drawer_directory(drawer_id, dir_key)
                if os.path.exists(path):
                    for item in os.listdir(path):
                        item_path = os.path.join(path, item)
                        (shutil.rmtree if os.path.isdir(item_path) else os.remove)(item_path)
                    cleared.append(f"{drawer_id}/{dir_key}")
            except Exception as e:
                log(f"Warning: Could not clear {drawer_id}/{dir_key}: {e}")

    if cleared:
        log(f"Cleared outputs from: {', '.join(cleared)}")


# ---------------------------------------------------------------------------
# Status report
# ---------------------------------------------------------------------------

STEP_OUTPUT_DIRS = {
    "resize_drawers":         "resized",
    "find_trays":             "coordinates",
    "crop_trays":             "trays",
    "resize_trays":           "resized_trays",
    "find_traylabels":        "label_coordinates",
    "crop_labels":            "labels",
    "find_specimens":         "resized_trays_coordinates",
    "crop_specimens":         "specimens",
    "create_traymaps":        "guides",
    "outline_specimens":      "mask_coordinates",
    "create_masks":           "mask_png",
    "measure_specimens":      "measurements",
    "censor_background":      "no_background",
    "outline_pins":           "pin_coordinates",
    "create_pinmask":         "full_masks",
    "create_transparency":    "transparencies",
    "transcribe_barcodes":    "tray_level",
    "transcribe_geocodes":    "tray_level",
    "transcribe_taxonomy":    "tray_level",
    "transcribe_specimens": "tray_context",
    "merge_data":             "data",
}

NESTED_OUTPUT_STEPS = {
    "crop_specimens", "outline_specimens", "create_masks",
    "censor_background", "outline_pins", "create_pinmask", "create_transparency",
}

SENTINEL_FILES = {
    "measure_specimens":      "measurements.csv",
    "transcribe_barcodes":    "unit_barcodes.csv",
    "transcribe_geocodes":    "geocodes.csv",
    "transcribe_taxonomy":    "taxonomy.csv",
    "transcribe_specimens": "group_localities.csv",
}


def _has_output(config, drawer_id, step) -> tuple:
    """
    Return (has_output: bool, extra: str | None) for a given step.
    extra carries the merge timestamp when relevant.
    """
    output_path = config.get_drawer_directory(drawer_id, STEP_OUTPUT_DIRS[step])

    if not os.path.exists(output_path):
        return False, None

    if step == "merge_data":
        dirs = [d for d in os.listdir(output_path)
                if os.path.isdir(os.path.join(output_path, d))]
        return bool(dirs), max(dirs) if dirs else None

    if step in SENTINEL_FILES:
        return os.path.exists(os.path.join(output_path, SENTINEL_FILES[step])), None

    if step in NESTED_OUTPUT_STEPS:
        for subdir in os.listdir(output_path):
            subdir_path = os.path.join(output_path, subdir)
            if os.path.isdir(subdir_path) and any(
                os.path.isfile(os.path.join(subdir_path, f))
                for f in os.listdir(subdir_path)
            ):
                return True, None
        return False, None

    return any(os.path.isfile(os.path.join(output_path, f)) for f in os.listdir(output_path)), None


def generate_status_report(config, write_report=False):
    discover_and_sort_drawers(config)
    available_drawers = config.get_existing_drawers()

    if not available_drawers:
        log("No drawers found")
        return

    log("=" * 80)
    log("DRAWER STATUS REPORT")
    log("=" * 80)

    report_data = []

    for drawer_id in available_drawers:
        drawer_type = "specimen-only" if is_specimen_only_drawer(config, drawer_id) else "standard"
        log(f"\n{drawer_id} ({drawer_type}):")
        log("-" * 40)

        complete, missing = [], []
        drawer_status = {"drawer_id": drawer_id}

        for step in STEP_OUTPUT_DIRS:
            try:
                has, extra = _has_output(config, drawer_id, step)
                if has:
                    complete.append(step)
                    drawer_status[step] = "complete"
                    if extra:
                        drawer_status["merge_data_timestamp"] = extra
                else:
                    missing.append(step)
                    drawer_status[step] = "missing"
            except Exception:
                missing.append(step)
                drawer_status[step] = "missing"

        if complete:
            log(f"  Complete: {', '.join(complete)}")
        if missing:
            log(f"  Missing:  {', '.join(missing)}")
        if "merge_data_timestamp" in drawer_status:
            log(f"  Most recent merge: {drawer_status['merge_data_timestamp']}")

        report_data.append(drawer_status)

    log("\n" + "=" * 80)

    if write_report:
        _write_status_csv(report_data)


def _write_status_csv(report_data):
    os.makedirs("status_reports", exist_ok=True)
    timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M")
    path = os.path.join("status_reports", f"status_report_{timestamp}.csv")
    fieldnames = ["drawer_id"] + list(STEP_OUTPUT_DIRS) + ["merge_data_timestamp"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report_data)
    log(f"Status report written to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    config = DrawerDissectConfig()
    start_time = time.time()

    try:
        args = parse_arguments()

        if args.status:
            generate_status_report(config, write_report=args.write_report)
            return

        if args.list_drawers:
            discover_and_sort_drawers(config)
            available = config.get_existing_drawers()
            if available:
                log("Available drawers:")
                for drawer in available:
                    dtype = "specimen-only" if is_specimen_only_drawer(config, drawer) else "standard"
                    log(f"  - {drawer} ({dtype})")
            else:
                log("No drawers found")
            return

        specified = [d.strip() for d in args.drawers.split(",")] if args.drawers else None
        drawers_to_process = get_drawers_to_process(config, specified)
        if not drawers_to_process:
            log("No drawers to process")
            return

        valid_drawers, specimen_only_drawers = [], []
        for drawer_id in drawers_to_process:
            if validate_drawer_structure(config, drawer_id):
                valid_drawers.append(drawer_id)
                if is_specimen_only_drawer(config, drawer_id):
                    specimen_only_drawers.append(drawer_id)
            else:
                log(f"Skipping invalid drawer: {drawer_id}")

        if not valid_drawers:
            log("No valid drawers to process")
            return

        steps_to_run = determine_steps(args)

        if args.rerun:
            if not confirm_rerun(steps_to_run, valid_drawers):
                log("Operation cancelled by user")
                return
            log("Clearing existing outputs...")
            for drawer_id in valid_drawers:
                clear_existing_outputs(config, drawer_id, steps_to_run)

        if specimen_only_drawers:
            skipped = [s for s in steps_to_run if s not in SPECIMEN_ONLY_STEPS]
            if skipped:
                log(f"Warning: {skipped} not supported for specimen-only drawers — will be skipped")

    except ValueError as e:
        log(f"Error: {e}")
        return

    log("DrawerDissect Pipeline")
    log("======================")
    log(f"Deployment:  {config.deployment}")
    log(f"Drawers:     {', '.join(valid_drawers)}")
    if specimen_only_drawers:
        log(f"Specimen-only: {', '.join(specimen_only_drawers)}")
    log(f"Steps:       {', '.join(steps_to_run)}")
    if args.rerun:
        log("Mode: RERUN (overwriting existing outputs)")

    for drawer_id in valid_drawers:
        log(f"\n{'='*20} Processing {drawer_id} {'='*20}")
        is_specimen_only = drawer_id in specimen_only_drawers

        drawer_steps = [
            s for s in steps_to_run
            if not (is_specimen_only and s not in SPECIMEN_ONLY_STEPS)
        ]

        if not drawer_steps:
            log(f"No valid steps to run for drawer {drawer_id}")
            continue

        for step in drawer_steps:
            log(f"Running {step} for {drawer_id}")
            run_step_for_drawer(step, config, drawer_id, args)

    total = time.time() - start_time
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        time_str = f"{int(h)}h {int(m)}m {s:.2f}s"
    elif m:
        time_str = f"{int(m)}m {s:.2f}s"
    else:
        time_str = f"{s:.2f}s"

    log("\n" + "=" * 50)
    log("Pipeline completed successfully")
    log(f"Total processing time: {time_str}")
    log("=" * 50)


if __name__ == "__main__":
    main()
