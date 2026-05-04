#!/usr/bin/env python3
"""
sort_specimens.py

Sort specimen images into train/valid/test folders organized by taxonomy,
ready for species-ID classification model training. Uses a 70/20/10 split
with sensible edge-case handling for taxa with very few specimens.

By default reads whitebg_specimens/ (masked specimens on a white background)
since that's the conventional input for image classifiers. Pass --unmasked
to use the raw specimens/ crops instead.

Strict gates are NOT applied — any specimen with a non-empty full_taxonomy
and a found image goes in. Curator approval, FMNH-INS#, and locality are
not required (this is training data, not a database upload).

Output structure (PyTorch / Keras compatible):

    advanced_outputs/classification_splits/<run_name>/
        train/
            Genus_species/
                <full_id>.tif
                ...
            Genus_species_subspecies/
                ...
        valid/
            Genus_species/
                ...
        test/
            ...
        manifest.csv     One row per copied image: drawer_id, full_id,
                         filename, full_taxonomy, folder_name, split,
                         src_path, dest_path. Lets you trace any image
                         in the splits back to its origin.
        run_log.txt

Split edge cases:
    n = 1  -> 1 train, 0 valid, 0 test (skipped from valid/test)
    n = 2  -> 1 train, 1 valid, 0 test
    n = 3+ -> 70/20/10 split with at-least-one in train and valid

Taxonomy folder names are normalized the same way as EMu image filenames:
    "Megacephala (Tetracha) virginica" -> "Megacephala_virginica"
    "Cicindela hamata monti"           -> "Cicindela_hamata_monti"
    "Habroscelimorpha dorsalis x venusta" -> "Habroscelimorpha_dorsalis_x_venusta"

Usage:
    python advanced_functions/sort_specimens.py --master_dir master_data/master_<...>
    python advanced_functions/sort_specimens.py --master_dir <PATH> --prefix Cicindelidae
    python advanced_functions/sort_specimens.py --master_dir <PATH> --unmasked
    python advanced_functions/sort_specimens.py --master_dir <PATH> --run_name my_split_v1
    python advanced_functions/sort_specimens.py --master_dir <PATH> --seed 7
"""

import argparse
import csv
import math
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable


# ── Constants ────────────────────────────────────────────────────────────────

DRAWERS_DIR_DEFAULT = "drawers"
OUTPUT_BASE = Path("advanced_outputs/classification_splits")
TIMESTAMP_FMT = "%Y-%m-%d-%H-%M"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff")

WHITEBG_FOLDER = "whitebg_specimens"
SPECIMENS_FOLDER = "specimens"

SPLIT_RATIOS = {"train": 0.70, "valid": 0.20, "test": 0.10}

MANIFEST_FILENAME = "manifest.csv"
MANIFEST_COLUMNS = [
    "drawer_id", "full_id", "filename", "full_taxonomy",
    "folder_name", "split", "src_path", "dest_path",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def resolve_master_dir(master_dir_arg: str) -> Path:
    master = Path(master_dir_arg)
    if not master.is_dir():
        print(f"[ERROR] master folder not found: {master}")
        sys.exit(1)
    return master


def normalize_taxonomy_for_folder(full_taxonomy: str) -> str:
    """Convert full_taxonomy to a filesystem-safe folder name.

    Same rules as EMu image filename taxonomy parsing:
      - Drop parentheticals (subgenera)
      - Keep subspecies
      - Handle hybrids: 'x' as standalone word collapses repeated parts
      - Sanitize to alphanumerics joined with underscores

    Returns 'unknown' if the input is empty or unparseable.
    """
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


def find_specimen_image(drawers_dir: Path, drawer_id: str, full_id: str,
                        source_folder: str) -> Path | None:
    """Recursively search drawers/<drawer_id>/<source_folder>/ for an image.

    Returns the first match found (case-insensitive on extension), or None.
    """
    root = drawers_dir / drawer_id / source_folder
    if not root.is_dir():
        return None
    for candidate in root.rglob(f"{full_id}.*"):
        if candidate.suffix.lower() in IMAGE_EXTENSIONS:
            return candidate
    return None


def split_indices(n: int, rng: random.Random) -> tuple:
    """Decide how many specimens go in each split based on n.

    Returns (n_train, n_valid, n_test) such that n_train + n_valid + n_test == n.
    """
    if n == 0:
        return (0, 0, 0)
    if n == 1:
        return (1, 0, 0)
    if n == 2:
        return (1, 1, 0)

    # n >= 3: aim for 70/20/10, but guarantee >= 1 in train and valid.
    n_test = math.floor(n * SPLIT_RATIOS["test"])
    n_valid = max(1, math.floor(n * SPLIT_RATIOS["valid"]))
    n_train = n - n_valid - n_test
    if n_train < 1:
        # Edge case for very tiny n (shouldn't happen with n>=3 + above floors)
        n_train, n_valid, n_test = max(1, n - 1), min(1, n - 1), 0
    return (n_train, n_valid, n_test)


def make_run_folder(prefixes: list, run_name: str | None) -> Path:
    """Build the timestamped output folder path.

    If run_name is provided, used verbatim (no timestamp). Otherwise, build
    from prefix(es) + timestamp.
    """
    if run_name:
        return OUTPUT_BASE / run_name

    timestamp = datetime.now().strftime(TIMESTAMP_FMT)
    if prefixes:
        cleaned = [p.rstrip("_") for p in prefixes]
        prefix_part = "+".join(cleaned)
        return OUTPUT_BASE / f"{prefix_part}_{timestamp}"
    return OUTPUT_BASE / f"all_{timestamp}"


# ── Main processing ──────────────────────────────────────────────────────────

def collect_specimens(master_specimens: Path, prefixes: list,
                      drawers_dir: Path, source_folder: str):
    """Walk master_specimens.csv, group by normalized taxonomy.

    Returns a dict {taxonomy_folder_name: list of specimen records}
    where each record is a dict with full_id, drawer_id, full_taxonomy, src.
    Specimens with no image found are skipped with a warning.
    """
    if not master_specimens.exists():
        print(f"[ERROR] master_specimens.csv not found at: {master_specimens}")
        sys.exit(1)

    by_taxonomy = defaultdict(list)
    n_scanned = 0
    n_no_taxonomy = 0
    n_no_image = 0
    skipped_image_examples = []

    with master_specimens.open(newline="") as f:
        for row in csv.DictReader(f):
            full_id = row.get("full_id", "")
            drawer_id = row.get("drawer_id", "")
            full_taxonomy = row.get("full_taxonomy", "")
            if not full_id:
                continue
            if prefixes and not any(drawer_id.startswith(p) for p in prefixes):
                continue

            n_scanned += 1

            if not full_taxonomy.strip():
                n_no_taxonomy += 1
                continue

            src_image = find_specimen_image(drawers_dir, drawer_id, full_id, source_folder)
            if src_image is None:
                n_no_image += 1
                if len(skipped_image_examples) < 5:
                    skipped_image_examples.append(full_id)
                continue

            tax_folder = normalize_taxonomy_for_folder(full_taxonomy)
            by_taxonomy[tax_folder].append({
                "full_id": full_id,
                "drawer_id": drawer_id,
                "full_taxonomy": full_taxonomy,
                "src": src_image,
            })

    return {
        "by_taxonomy": by_taxonomy,
        "n_scanned": n_scanned,
        "n_no_taxonomy": n_no_taxonomy,
        "n_no_image": n_no_image,
        "skipped_image_examples": skipped_image_examples,
    }


def split_and_copy(by_taxonomy: dict, run_folder: Path, rng: random.Random):
    """Apply 70/20/10 split per taxon, copy images, build manifest rows.

    Returns (split_summary, manifest_rows).
    """
    summary = {}
    manifest_rows = []
    total_files = sum(len(v) for v in by_taxonomy.values())
    pbar = tqdm(total=total_files, desc="Copying images", unit="img", leave=False)

    for tax_folder, specimens in sorted(by_taxonomy.items()):
        # Shuffle deterministically (rng is seeded)
        shuffled = specimens[:]
        rng.shuffle(shuffled)

        n = len(shuffled)
        n_train, n_valid, n_test = split_indices(n, rng)

        splits = {
            "train": shuffled[:n_train],
            "valid": shuffled[n_train:n_train + n_valid],
            "test":  shuffled[n_train + n_valid:n_train + n_valid + n_test],
        }

        for split_name, items in splits.items():
            if not items:
                continue
            target_dir = run_folder / split_name / tax_folder
            target_dir.mkdir(parents=True, exist_ok=True)
            for spec in items:
                src = spec["src"]
                full_id = spec["full_id"]
                filename = f"{full_id}{src.suffix}"
                dest = target_dir / filename
                try:
                    shutil.copy2(src, dest)
                except Exception as e:
                    print(f"  [ERROR] {full_id}: copy failed -- {e}")
                    pbar.update(1)
                    continue
                manifest_rows.append({
                    "drawer_id": spec["drawer_id"],
                    "full_id": full_id,
                    "filename": filename,
                    "full_taxonomy": spec["full_taxonomy"],
                    "folder_name": tax_folder,
                    "split": split_name,
                    "src_path": str(src),
                    "dest_path": str(dest),
                })
                pbar.update(1)

        summary[tax_folder] = {
            "n_total": n,
            "n_train": n_train,
            "n_valid": n_valid,
            "n_test": n_test,
        }

    pbar.close()
    return summary, manifest_rows


def write_manifest(manifest_path: Path, rows: list):
    """Write the manifest CSV with header row."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


# ── Output ───────────────────────────────────────────────────────────────────

def write_run_log(log_path: Path, args, master_dir: Path, source_folder: str,
                  collect_result: dict, split_summary: dict, seed: int):
    n_train_total = sum(s["n_train"] for s in split_summary.values())
    n_valid_total = sum(s["n_valid"] for s in split_summary.values())
    n_test_total = sum(s["n_test"] for s in split_summary.values())
    n_taxa = len(split_summary)

    command = f"python {Path(sys.argv[0]).name} " + " ".join(sys.argv[1:])
    with log_path.open("w") as f:
        f.write("DrawerDissect sort_specimens run\n")
        f.write("=" * 50 + "\n")
        f.write(f"Timestamp        : {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Command          : {command}\n")
        f.write(f"Master input     : {master_dir}\n")
        f.write(f"Drawers dir      : {Path(args.drawers_dir).absolute()}\n")
        f.write(f"Source folder    : {source_folder}\n")
        f.write(f"Random seed      : {seed}\n")
        f.write(f"Prefix(es)       : {', '.join(args.prefix) if args.prefix else '(all drawers)'}\n")
        f.write(f"\nResults:\n")
        f.write(f"  Specimens scanned         : {collect_result['n_scanned']}\n")
        f.write(f"  Skipped (no taxonomy)     : {collect_result['n_no_taxonomy']}\n")
        f.write(f"  Skipped (no image found)  : {collect_result['n_no_image']}\n")
        f.write(f"  Specimens copied          : {n_train_total + n_valid_total + n_test_total}\n")
        f.write(f"  Taxa                      : {n_taxa}\n")
        f.write(f"  Train / Valid / Test      : {n_train_total} / {n_valid_total} / {n_test_total}\n")

        if collect_result["skipped_image_examples"]:
            f.write(f"\nFirst few specimens missing images:\n")
            for ex in collect_result["skipped_image_examples"]:
                f.write(f"  {ex}\n")

        f.write(f"\nPer-taxon breakdown:\n")
        f.write(f"  {'Taxon':<50} {'Total':>6} {'Train':>6} {'Valid':>6} {'Test':>6}\n")
        for tax in sorted(split_summary.keys()):
            s = split_summary[tax]
            f.write(f"  {tax:<50} {s['n_total']:>6} {s['n_train']:>6} {s['n_valid']:>6} {s['n_test']:>6}\n")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--master_dir", metavar="PATH", required=True,
                        help="Path to the master_<timestamp>/ run folder.")
    parser.add_argument("--prefix", nargs="+", default=[],
                        help="Only include specimens whose drawer_id starts with these prefixes")
    parser.add_argument("--drawers_dir", default=DRAWERS_DIR_DEFAULT,
                        help=f"Active drawers directory (default: '{DRAWERS_DIR_DEFAULT}')")
    parser.add_argument("--unmasked", action="store_true",
                        help=f"Use raw {SPECIMENS_FOLDER}/ images instead of {WHITEBG_FOLDER}/ (default)")
    parser.add_argument("--run_name", metavar="NAME",
                        help="Custom name for the output folder (default: <prefix>_<timestamp>)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducible splits (default: 42)")
    args = parser.parse_args()

    # Resolve inputs
    master_dir = resolve_master_dir(args.master_dir)
    master_specimens_csv = master_dir / "master_specimens.csv"
    drawers_dir = Path(args.drawers_dir)
    source_folder = SPECIMENS_FOLDER if args.unmasked else WHITEBG_FOLDER

    # Collect
    collect_result = collect_specimens(
        master_specimens_csv, args.prefix, drawers_dir, source_folder,
    )
    by_taxonomy = collect_result["by_taxonomy"]

    if not by_taxonomy:
        print(f"\n[ERROR] No specimens collected.")
        print(f"        Scanned: {collect_result['n_scanned']}")
        print(f"        No taxonomy: {collect_result['n_no_taxonomy']}")
        print(f"        No image: {collect_result['n_no_image']}")
        sys.exit(1)

    # Output paths
    run_folder = make_run_folder(args.prefix, args.run_name)
    if run_folder.exists():
        print(f"[ERROR] Run folder already exists: {run_folder}")
        print(f"        Use a different --run_name or delete the existing folder.")
        sys.exit(1)
    run_folder.mkdir(parents=True, exist_ok=True)
    log_path = run_folder / "run_log.txt"

    # Split and copy
    rng = random.Random(args.seed)
    split_summary, manifest_rows = split_and_copy(by_taxonomy, run_folder, rng)

    # Write manifest CSV
    manifest_path = run_folder / MANIFEST_FILENAME
    write_manifest(manifest_path, manifest_rows)

    # Write log
    write_run_log(log_path, args, master_dir, source_folder,
                  collect_result, split_summary, args.seed)

    # Summary
    n_train = sum(s["n_train"] for s in split_summary.values())
    n_valid = sum(s["n_valid"] for s in split_summary.values())
    n_test = sum(s["n_test"] for s in split_summary.values())
    n_taxa = len(split_summary)

    # Distribution of class sizes (so user can see if any taxa are very small)
    class_sizes = Counter()
    for s in split_summary.values():
        n = s["n_total"]
        if n == 1:
            class_sizes["n=1 (train only)"] += 1
        elif n == 2:
            class_sizes["n=2 (train+valid only)"] += 1
        elif n < 10:
            class_sizes["n=3-9"] += 1
        else:
            class_sizes["n>=10 (full split)"] += 1

    print(f"\n── Sort summary ─────────────────────────────")
    print(f"  Master input         : {master_dir}")
    print(f"  Output folder        : {run_folder}")
    print(f"  Manifest             : {manifest_path}")
    print(f"  Source images        : {source_folder}/")
    print(f"  Random seed          : {args.seed}")
    print(f"  Specimens scanned    : {collect_result['n_scanned']}")
    if collect_result["n_no_taxonomy"]:
        print(f"  Skipped (no taxonomy): {collect_result['n_no_taxonomy']}")
    if collect_result["n_no_image"]:
        print(f"  Skipped (no image)   : {collect_result['n_no_image']}")
        for ex in collect_result["skipped_image_examples"]:
            print(f"    - {ex}")
        if collect_result["n_no_image"] > len(collect_result["skipped_image_examples"]):
            extra = collect_result["n_no_image"] - len(collect_result["skipped_image_examples"])
            print(f"    ... and {extra} more (see run_log.txt)")
    print(f"  Taxa                 : {n_taxa}")
    print(f"  Train / Valid / Test : {n_train} / {n_valid} / {n_test}")

    if class_sizes:
        print(f"\n  Class size distribution:")
        for label, n in [
            ("n=1 (train only)", class_sizes.get("n=1 (train only)", 0)),
            ("n=2 (train+valid only)", class_sizes.get("n=2 (train+valid only)", 0)),
            ("n=3-9", class_sizes.get("n=3-9", 0)),
            ("n>=10 (full split)", class_sizes.get("n>=10 (full split)", 0)),
        ]:
            if n:
                print(f"    {label:<25} {n:>5} taxa")


if __name__ == "__main__":
    main()
