#!/usr/bin/env python3
"""
archive_drawers.py

Move drawer folders into compressed zip archives to free up disk space,
or restore archived drawers back into the active drawers/ directory.

Archive mode (default — LEAN):
    By default, only the bare minimum needed to reconstruct results is
    kept. Output crops, masks, and other derived images are deleted along
    with the source folder.

    ALWAYS kept:
        - Original drawer image (drawers/<drawer_id>/fullsize/)
        - All .json files (coordinates, mask polygons, etc.)
        - All .csv files (transcriptions, measurements, etc.)
    Use these flags to also keep specific image categories:
        --keep_specimens         keep specimens/   (cropped specimen images)
        --keep_trays             keep trays/       (cropped tray images)
        --keep_transparencies    keep transparencies/ (transparent-bg specimens)
    DELETED unless flagged:
        - whitebg_specimens, labels, masks, resized images, guides
        - The original drawer folder itself, after the zip is verified

Restore mode (--restore):
    - Extracts each matching zip back into drawers/<drawer_id>/
    - Leaves the zip file in place (so the archive remains a backup)
    - Skips drawers whose folder already exists (unless --rerun)

You must specify either --prefix or --all to select what to act on.
A confirmation prompt with full kept/deleted breakdown is shown before
any destructive action.

Usage:
    # Archive (lean by default)
    python advanced_functions/archive_drawers.py --prefix 34_4_10
    python advanced_functions/archive_drawers.py --all --keep_specimens
    python advanced_functions/archive_drawers.py --prefix 34_4_10 --keep_trays --keep_transparencies
    python advanced_functions/archive_drawers.py --prefix 34_4_10 --rerun  # overwrite existing zip

    # Restore
    python advanced_functions/archive_drawers.py --restore --prefix 34_4_10
    python advanced_functions/archive_drawers.py --restore --all
    python advanced_functions/archive_drawers.py --restore --prefix 34_4_10 --rerun  # overwrite existing folder
"""

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    # Fallback: no progress bar, but the script still works.
    # `pip install tqdm` to enable it.
    def tqdm(iterable, **kwargs):
        return iterable

DRAWERS_DIR_DEFAULT = "drawers"
ARCHIVE_DIR_DEFAULT = "archive"


# ── Size helpers ────────────────────────────────────────────────────────────

def folder_size_mb(folder: Path) -> float:
    total = sum(f.stat().st_size for f in folder.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def file_size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


# ── Selection ───────────────────────────────────────────────────────────────

def select_drawers_to_archive(drawers_dir: Path, prefixes: list, archive_dir: Path, rerun: bool):
    """Return list of (drawer_path, archive_path) pairs to archive."""
    if not drawers_dir.is_dir():
        print(f"[ERROR] drawers directory not found: {drawers_dir}")
        sys.exit(1)

    selected = []
    for d in sorted(drawers_dir.iterdir()):
        if not d.is_dir():
            continue
        if prefixes and not any(d.name.startswith(p) for p in prefixes):
            continue
        archive_path = archive_dir / f"{d.name}.zip"
        if archive_path.exists() and not rerun:
            print(f"  [SKIP] {d.name}: archive already exists (use --rerun to overwrite)")
            continue
        selected.append((d, archive_path))
    return selected


def select_archives_to_restore(archive_dir: Path, prefixes: list, drawers_dir: Path, rerun: bool):
    """Return list of (archive_path, drawer_path) pairs to restore."""
    if not archive_dir.is_dir():
        print(f"[ERROR] archive directory not found: {archive_dir}")
        sys.exit(1)

    selected = []
    for z in sorted(archive_dir.glob("*.zip")):
        drawer_name = z.stem
        if prefixes and not any(drawer_name.startswith(p) for p in prefixes):
            continue
        drawer_path = drawers_dir / drawer_name
        if drawer_path.exists() and not rerun:
            print(f"  [SKIP] {drawer_name}: drawer folder already exists (use --rerun to overwrite)")
            continue
        selected.append((z, drawer_path))
    return selected


# ── File selection (lean archival) ──────────────────────────────────────────

# Files anywhere in the tree always kept by extension (data files)
ALWAYS_KEEP_EXTENSIONS = {".json", ".csv"}

# File extensions treated as already-compressed images. These get stored in
# the zip without DEFLATE (which is slow and gains ~3% on JPEG/TIFF/PNG).
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}

# Subfolder names (relative to drawer root) whose entire contents are always
# kept. From config.yaml `directories.drawer_subdirs`. The fullsize/ folder
# holds the original source image — losing it makes the archive useless.
ALWAYS_KEEP_FOLDERS = {"fullsize"}

# Optional folders, kept only when the corresponding flag is set
OPTIONAL_FOLDERS = {
    "specimens": "keep_specimens",            # full-size specimen crops
    "trays": "keep_trays",                    # full-size tray crops
    "transparencies": "keep_transparencies",  # transparent-background specimens
}


def should_keep(file_path: Path, drawer_path: Path,
                keep_specimens: bool, keep_trays: bool,
                keep_transparencies: bool) -> bool:
    """Decide whether a file should be included in the archive.

    Rule:
      - Always keep .json and .csv files (data is the irreplaceable thing)
      - Always keep everything in fullsize/ (original drawer image)
      - Conditionally keep specimens/, trays/, transparencies/ based on flags
      - Drop everything else (regenerable from above)
    """
    # Always-keep extensions
    if file_path.suffix.lower() in ALWAYS_KEEP_EXTENSIONS:
        return True

    # Top-level folder under the drawer root
    try:
        rel_parts = file_path.relative_to(drawer_path).parts
    except ValueError:
        return False
    if not rel_parts:
        return False
    top_folder = rel_parts[0]

    if top_folder in ALWAYS_KEEP_FOLDERS:
        return True
    if top_folder == "specimens" and keep_specimens:
        return True
    if top_folder == "trays" and keep_trays:
        return True
    if top_folder == "transparencies" and keep_transparencies:
        return True
    return False


def filter_files(drawer_path: Path, keep_specimens: bool, keep_trays: bool,
                 keep_transparencies: bool) -> list:
    """Return list of files in the drawer that should be included in the archive."""
    return [
        f for f in drawer_path.rglob("*")
        if f.is_file() and should_keep(f, drawer_path,
                                       keep_specimens, keep_trays, keep_transparencies)
    ]


def files_size_mb(files: list) -> float:
    """Total size in MB of a list of files."""
    return sum(f.stat().st_size for f in files) / (1024 * 1024)


# ── Operations ──────────────────────────────────────────────────────────────

def archive_drawer(drawer_path: Path, archive_path: Path,
                   keep_specimens: bool, keep_trays: bool,
                   keep_transparencies: bool):
    """Zip the kept files atomically: write to .tmp, verify, rename, delete original.

    Only files that pass should_keep() go into the zip. The source folder
    (including all unzipped/excluded files) is deleted only after the zip
    has been verified.
    """
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = archive_path.with_suffix(".zip.tmp")

    # Collect file list up front so tqdm knows the total
    files = filter_files(drawer_path, keep_specimens, keep_trays, keep_transparencies)

    # Per-file compression mode:
    #   - Image files (TIFF/JPEG/PNG): ZIP_STORED — already compressed; DEFLATE
    #     on a 1+ GB TIFF can take many minutes for ~3% size reduction.
    #   - Everything else (.json, .csv, etc.): ZIP_DEFLATED — text data
    #     compresses dramatically (often 70-90% smaller).
    # This is the difference between a multi-hour archive run and a few minutes.
    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in tqdm(files, desc=f"  Zipping  {drawer_path.name}", unit="file", leave=False):
            # Store paths relative to drawer_path's parent so the zip
            # contains the drawer folder name at its root
            arcname = f.relative_to(drawer_path.parent)
            mode = (zipfile.ZIP_STORED
                    if f.suffix.lower() in IMAGE_EXTENSIONS
                    else zipfile.ZIP_DEFLATED)
            zf.write(f, arcname, compress_type=mode)

    # Verify the zip is readable
    with zipfile.ZipFile(tmp_path, "r") as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f"zip verification failed; corrupt entry: {bad}")

    # Atomic rename, then delete the original folder
    if archive_path.exists():
        archive_path.unlink()
    tmp_path.rename(archive_path)
    shutil.rmtree(drawer_path)


def restore_archive(archive_path: Path, drawer_path: Path, drawers_dir: Path):
    """Extract a zip back into drawers_dir."""
    if drawer_path.exists():
        shutil.rmtree(drawer_path)
    with zipfile.ZipFile(archive_path, "r") as zf:
        members = zf.namelist()
        for m in tqdm(members, desc=f"  Restoring {archive_path.stem}", unit="file", leave=False):
            zf.extract(m, drawers_dir)


# ── Modes ───────────────────────────────────────────────────────────────────

def confirm_yes(prompt: str) -> bool:
    return input(prompt).strip().lower() == "yes"


def run_archive(drawers_dir: Path, archive_dir: Path, prefixes: list, rerun: bool,
                keep_specimens: bool, keep_trays: bool, keep_transparencies: bool):
    selected = select_drawers_to_archive(drawers_dir, prefixes, archive_dir, rerun)

    if not selected:
        print("\nNo drawers to archive.")
        return

    # Pre-compute kept-file lists so the plan can show before-vs-after sizes
    plans = []
    for drawer_path, archive_path in selected:
        kept = filter_files(drawer_path, keep_specimens, keep_trays, keep_transparencies)
        plans.append({
            "drawer_path": drawer_path,
            "archive_path": archive_path,
            "kept_files": kept,
            "total_mb": folder_size_mb(drawer_path),
            "kept_mb": files_size_mb(kept),
        })

    # Show plan
    print(f"\n── Archive plan ──────────────────────────────")
    total_before = 0.0
    total_after = 0.0
    for p in plans:
        total_before += p["total_mb"]
        total_after += p["kept_mb"]
        print(f"  {p['drawer_path'].name:<40} "
              f"{p['total_mb']:>8.1f} MB → {p['kept_mb']:>7.1f} MB kept")
    print(f"  {'TOTAL':<40} "
          f"{total_before:>8.1f} MB → {total_after:>7.1f} MB across {len(plans)} drawer(s)")
    saved = total_before - total_after
    if total_before > 0:
        pct = 100 * saved / total_before
        print(f"  Saving ~{saved:,.1f} MB ({pct:.0f}%) before zip compression")

    # Explicit kept/deleted breakdown
    print(f"\n⚠  WHAT WILL BE KEPT (zipped into archive):")
    print(f"   - Original drawer image  (fullsize/)")
    print(f"   - All .json files        (coordinates, mask polygons, etc.)")
    print(f"   - All .csv files         (transcriptions, measurements, etc.)")
    if keep_specimens:
        print(f"   - Specimen crops         (specimens/)")
    if keep_trays:
        print(f"   - Tray crops             (trays/)")
    if keep_transparencies:
        print(f"   - Transparency images    (transparencies/)")

    print(f"\n⚠  WHAT WILL BE PERMANENTLY DELETED:")
    if not keep_specimens:
        print(f"   - Specimen crops         (use --keep_specimens to retain)")
    if not keep_trays:
        print(f"   - Tray crops             (use --keep_trays to retain)")
    if not keep_transparencies:
        print(f"   - Transparency images    (use --keep_transparencies to retain)")
    print(f"   - White-bg specimens, labels, masks, resized images, guides")
    print(f"   - Source drawer folders themselves (after zip verification)")

    if not confirm_yes("\nType 'yes' to proceed: "):
        print("Aborted.")
        return

    # Execute
    print()
    successes, failures = [], []
    for p in plans:
        drawer_path = p["drawer_path"]
        archive_path = p["archive_path"]
        try:
            archive_drawer(drawer_path, archive_path,
                          keep_specimens, keep_trays, keep_transparencies)
            zip_mb = file_size_mb(archive_path)
            print(f"  [OK]    {drawer_path.name} → {archive_path.name} ({zip_mb:.1f} MB)")
            successes.append(drawer_path.name)
        except Exception as e:
            print(f"  [ERROR] {drawer_path.name}: {e}")
            failures.append(drawer_path.name)

    # Summary
    print(f"\n── Summary ──────────────────────────────────")
    print(f"  Archived: {len(successes)}")
    if failures:
        print(f"  Failed  : {len(failures)}")
        for n in failures:
            print(f"    - {n}")


def run_restore(drawers_dir: Path, archive_dir: Path, prefixes: list, rerun: bool):
    selected = select_archives_to_restore(archive_dir, prefixes, drawers_dir, rerun)

    if not selected:
        print("\nNo archives to restore.")
        return

    # Show plan
    print(f"\n── Restore plan ──────────────────────────────")
    for archive_path, drawer_path in selected:
        size = file_size_mb(archive_path)
        print(f"  {archive_path.name:<44} {size:>8.1f} MB → {drawer_path}")
    print(f"\nNote: zip files will remain in {archive_dir}/ after restore.")

    if not confirm_yes("\nType 'yes' to proceed: "):
        print("Aborted.")
        return

    # Execute
    print()
    drawers_dir.mkdir(parents=True, exist_ok=True)
    successes, failures = [], []
    for archive_path, drawer_path in selected:
        try:
            restore_archive(archive_path, drawer_path, drawers_dir)
            print(f"  [OK]    {archive_path.name} → {drawer_path}")
            successes.append(drawer_path.name)
        except Exception as e:
            print(f"  [ERROR] {archive_path.name}: {e}")
            failures.append(drawer_path.name)

    # Summary
    print(f"\n── Summary ──────────────────────────────────")
    print(f"  Restored: {len(successes)}")
    if failures:
        print(f"  Failed  : {len(failures)}")
        for n in failures:
            print(f"    - {n}")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--restore", action="store_true",
                        help="Restore mode: extract archives back into drawers/")

    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--prefix", nargs="+", default=None,
                          help="Select drawers/archives whose names start with these prefix(es)")
    selector.add_argument("--all", action="store_true",
                          help="Select ALL drawers/archives")

    parser.add_argument("--drawers_dir", default=DRAWERS_DIR_DEFAULT,
                        help=f"Active drawers directory (default: '{DRAWERS_DIR_DEFAULT}')")
    parser.add_argument("--archive_dir", default=ARCHIVE_DIR_DEFAULT,
                        help=f"Archive directory (default: '{ARCHIVE_DIR_DEFAULT}')")
    parser.add_argument("--rerun", action="store_true",
                        help="Overwrite the destination if it already exists")
    parser.add_argument("--keep_specimens", action="store_true",
                        help="Also keep specimens/ folder (cropped specimen images)")
    parser.add_argument("--keep_trays", action="store_true",
                        help="Also keep trays/ folder (cropped tray images)")
    parser.add_argument("--keep_transparencies", action="store_true",
                        help="Also keep transparencies/ folder (transparent-bg specimens)")
    args = parser.parse_args()

    drawers_dir = Path(args.drawers_dir)
    archive_dir = Path(args.archive_dir)
    prefixes = [] if args.all else args.prefix  # [] means "match everything"

    if args.restore:
        run_restore(drawers_dir, archive_dir, prefixes, args.rerun)
    else:
        run_archive(drawers_dir, archive_dir, prefixes, args.rerun,
                   args.keep_specimens, args.keep_trays, args.keep_transparencies)


if __name__ == "__main__":
    main()