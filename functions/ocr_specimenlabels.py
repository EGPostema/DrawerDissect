"""
ocr_traycontext.py
------------------
Tray-level specimen label transcription using multi-crop approach.

For each tray, this module:
  1. Finds all specimen crops and runs bugcleaner to filter out textless ones
  2. Sends to Claude in one call (batched if >20 specimens):
     - Tray header context (geocode, taxonomy, barcode) from existing CSVs
     - A downsized tray image for spatial context (optional, configurable)
     - All passing specimen crops as separate labeled images
  3. Runs Python-side validation (geocode cross-check, flag aggregation)
  4. Writes specimen_localities.csv (one row per specimen)

Drop this file into functions/.
"""

import os
import re
import csv
import json
import base64
import ast
import io
from pathlib import Path

from PIL import Image
from logging_utils import log, log_found

from functions.model_runner import build_model_runner
from functions.geocode_lookup import check_geocode_country, check_ambiguous_locality


# ===================================================================
# 1. BUGCLEANER
# ===================================================================

def run_bugcleaner_on_crop(crop_path, runner, confidence_threshold=95):
    """
    Run bugcleaner on a single specimen crop.
    Returns True if text detected above threshold, False otherwise.
    """
    try:
        result = runner.predict(crop_path)

        if hasattr(result, "json"):
            result = result.json()

        # Classification format: top-level "top" key
        if isinstance(result, dict) and "top" in result:
            top_class = result.get("top", "")
            top_conf = result.get("confidence", 0)
            if isinstance(top_conf, (int, float)):
                top_conf = top_conf * 100 if top_conf <= 1 else top_conf
            return top_class == "text" and top_conf >= confidence_threshold

        # Detection/classification with predictions list
        if isinstance(result, dict) and "predictions" in result:
            preds = result["predictions"]
        elif isinstance(result, list):
            preds = result
        else:
            preds = [result]

        for pred in preds:
            cls = pred.get("class", pred.get("top", ""))
            conf = pred.get("confidence", 0)
            if isinstance(conf, (int, float)):
                conf = conf * 100 if conf <= 1 else conf
            if cls == "text" and conf >= confidence_threshold:
                return True
        return False

    except Exception as e:
        log(f"  Warning: bugcleaner failed on {crop_path}: {e}")
        return True


# ===================================================================
# 2. IMAGE ENCODING
# ===================================================================

def encode_image_for_api(image_path, max_long_edge=800, quality=85):
    """
    Load an image, resize to max_long_edge, convert to JPEG,
    return base64 string + media type.
    """
    img = Image.open(image_path)

    long_edge = max(img.size)
    if long_edge > max_long_edge:
        scale = max_long_edge / long_edge
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.LANCZOS,
        )

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    b64 = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    return b64, "image/jpeg"


# ===================================================================
# 3. TRAY CONTEXT — gather header transcriptions
# ===================================================================

def build_tray_context_string(tray_level_dir, tray_name):
    """
    Gather tray-header transcriptions and return (context_string, geocode_value).
    """
    geocode_value = ""

    if not tray_level_dir or not os.path.exists(tray_level_dir):
        return "No tray header data available.", geocode_value

    context_parts = []

    header_files = {
        "taxonomy.csv":      "taxonomy",
        "geocodes.csv":      "geocode",
        "unit_barcodes.csv": "barcode",
    }

    for csv_name, label in header_files.items():
        csv_path = os.path.join(tray_level_dir, csv_name)
        if not os.path.isfile(csv_path):
            continue
        try:
            with open(csv_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tray_col = None
                    for candidate in ("tray", "image", "filename", "tray_id"):
                        if candidate in row:
                            tray_col = candidate
                            break
                    if tray_col is None:
                        continue

                    row_tray = Path(row[tray_col]).stem
                    if tray_name in row_tray or row_tray in tray_name:
                        for k, v in row.items():
                            if k == tray_col:
                                continue
                            if v and v.strip() and v.strip().lower() not in ("none", "null", "n/a", "unk"):
                                context_parts.append(f"  {label} - {k}: {v.strip()}")
                                if label == "geocode" and k == "geocode":
                                    geocode_value = v.strip().upper()
        except Exception:
            continue

    if not context_parts:
        return "No tray header data available.", geocode_value

    return "Tray header context:\n" + "\n".join(context_parts), geocode_value


# ===================================================================
# 4. FIND TRAY IMAGE
# ===================================================================

def find_tray_image(resized_trays_dir, tray_name, tray_stem):
    """Find the resized tray image for spatial context."""
    for ext in (".jpg", ".jpeg", ".png"):
        for name_variant in (tray_stem, tray_name):
            candidate = os.path.join(resized_trays_dir, name_variant + ext)
            if os.path.isfile(candidate):
                return candidate

    # Scan directory as fallback
    for f in os.listdir(resized_trays_dir):
        if tray_name in f and f.lower().endswith((".jpg", ".jpeg", ".png")):
            return os.path.join(resized_trays_dir, f)

    return None


# ===================================================================
# 5. CLAUDE CALL — tray image + individual crops + header context
# ===================================================================

def call_claude_multicrop(
    tray_image_path,
    specimen_crops,
    tray_context_str,
    api_key,
    model,
    max_tokens,
    system_prompt,
    user_prompt,
    include_tray_image=True,
):
    """
    One Claude call with: optional tray image + all specimen crops + context.
    Returns parsed response (list of group dicts), or None.
    """
    import anthropic

    # Fill in user prompt template
    user_text = user_prompt.replace("{tray_context}", tray_context_str)
    user_text = user_text.replace("{specimen_ids}", ", ".join(specimen_crops.keys()))

    # Build content — context first, then images, then instructions
    content = []

    # First: tray header context (geocode, taxonomy, barcode) so Claude is primed
    content.append({
        "type": "text",
        "text": f"TRAY HEADER CONTEXT:\n{tray_context_str}",
    })

    # Then: the tray overview image (if enabled)
    if include_tray_image and tray_image_path:
        content.append({
            "type": "text",
            "text": "TRAY OVERVIEW (use this to see spatial layout, row arrangement, and label patterns):",
        })
        tray_b64, tray_media = encode_image_for_api(tray_image_path, max_long_edge=1500, quality=85)
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": tray_media, "data": tray_b64},
        })
    else:
        content.append({
            "type": "text",
            "text": "No tray overview image provided. Use only the individual specimen crops below.",
        })

    # Then: each specimen crop, labeled
    content.append({
        "type": "text",
        "text": "INDIVIDUAL SPECIMEN CROPS (use these to read label text):",
    })
    for spec_id, crop_path in specimen_crops.items():
        content.append({"type": "text", "text": f"{spec_id}:"})
        crop_b64, crop_media = encode_image_for_api(crop_path, max_long_edge=800, quality=85)
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": crop_media, "data": crop_b64},
        })

    # Finally: the instructions
    content.append({"type": "text", "text": user_text})

    client = anthropic.Anthropic(api_key=api_key)

    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": content}],
            )
            raw = response.content[0].text.strip()
            tokens_in = response.usage.input_tokens
            tokens_out = response.usage.output_tokens
            log(f"    Tokens: {tokens_in} in / {tokens_out} out")

            result = parse_claude_response(raw)
            if result is not None:
                return result

            if attempt < max_attempts - 1:
                log(f"    Parse failed, retrying...")
                continue
            return None

        except Exception as e:
            log(f"  Claude API error: {e}")
            if attempt < max_attempts - 1:
                log(f"    Retrying...")
                continue
            return None


def parse_claude_response(raw_text):
    """Parse Claude's JSON response into a list of group dicts."""
    cleaned = raw_text
    if "```" in cleaned:
        cleaned = re.sub(r"```(?:json)?\s*", "", cleaned)
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "groups" in parsed:
            return parsed["groups"]
        if isinstance(parsed, list):
            return parsed
        return [parsed]
    except json.JSONDecodeError:
        pass

    try:
        parsed = ast.literal_eval(cleaned)
        if isinstance(parsed, dict) and "groups" in parsed:
            return parsed["groups"]
        if isinstance(parsed, list):
            return parsed
        return [parsed]
    except Exception:
        pass

    log(f"  Warning: could not parse Claude response.")
    return None


# ===================================================================
# 6. PYTHON-SIDE VALIDATION
# ===================================================================

def validate_groups(groups, geocode_value):
    """Run post-Claude validation. Modifies groups in place."""
    for group in groups:
        flags = group.get("flags", [])
        if isinstance(flags, str):
            flags = [f.strip() for f in flags.split(";") if f.strip()]

        country = group.get("country", "")
        state_province = group.get("stateProvince", group.get("state_province", ""))
        locality = group.get("locality", "")
        municipality = group.get("municipality", "")

        # Geocode vs. country
        if geocode_value and country:
            geo_flag = check_geocode_country(geocode_value, country)
            if geo_flag and geo_flag not in flags:
                flags.append(geo_flag)

        # Ambiguous locality
        amb_flag = check_ambiguous_locality(country, state_province, locality, municipality)
        if amb_flag and amb_flag not in flags:
            flags.append(amb_flag)

        # Clean DarwinCore fields
        darwincore_fields = ["country", "stateProvince", "state_province",
                            "county", "municipality", "locality",
                            "collector", "date"]
        for field in darwincore_fields:
            val = group.get(field, "")
            if isinstance(val, str):
                cleaned = re.sub(r'\[(\?|illegible|illeg\.)\]', '', val).strip()
                if not cleaned or cleaned in (",", "|", "-"):
                    group[field] = ""
                elif cleaned != val:
                    group[field] = cleaned

        # Normalize 'none'/'null' to empty
        for field in darwincore_fields + ["verbatim_text"]:
            val = group.get(field, "")
            if isinstance(val, str) and val.strip().lower() in ("none", "null", "n/a"):
                group[field] = ""

        group["flags"] = flags


# ===================================================================
# 7. OUTPUT
# ===================================================================

def write_outputs(groups, tray_name, notext_specimens, output_dir, model_name=""):
    """Write specimen_localities.csv (appending). One row per specimen."""
    specimen_path = os.path.join(output_dir, "specimen_localities.csv")

    specimen_fields = [
        "tray", "specimen_id", "label_group", "match_type",
        "verbatim_text",
        "country", "stateProvince", "county", "municipality", "locality",
        "collector", "date",
        "flags", "model",
    ]

    def _flatten_group(g, tray):
        row = {"tray": tray, "model": model_name}
        for field in ("label_group", "match_type", "verbatim_text",
                      "country", "stateProvince", "state_province",
                      "county", "municipality", "locality",
                      "collector", "date"):
            val = g.get(field, "")
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            if isinstance(val, str) and val.strip().lower() in ("none", "null", "n/a"):
                val = ""
            row[field] = val

        if not row.get("stateProvince") and row.get("state_province"):
            row["stateProvince"] = row.pop("state_province")
        row.pop("state_province", None)

        flags = g.get("flags", [])
        row["flags"] = "; ".join(str(f) for f in flags) if isinstance(flags, list) else str(flags)
        return row

    specimen_exists = os.path.isfile(specimen_path)
    with open(specimen_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=specimen_fields, extrasaction="ignore")
        if not specimen_exists:
            writer.writeheader()
        if groups:
            for g in groups:
                row_base = _flatten_group(g, tray_name)
                spec_ids = g.get("specimen_ids", [])
                if isinstance(spec_ids, str):
                    spec_ids = [s.strip() for s in spec_ids.split(",")]
                for spec_id in spec_ids:
                    row = dict(row_base)
                    row["specimen_id"] = spec_id
                    writer.writerow(row)

        for spec_id in notext_specimens:
            row = {"tray": tray_name, "specimen_id": spec_id, "match_type": "no_text_detected",
                   "model": model_name}
            row["flags"] = "no_text"
            for field in specimen_fields:
                if field not in row:
                    row[field] = ""
            writer.writerow(row)


# ===================================================================
# 8. MAIN ENTRY POINT
# ===================================================================

def process_tray_context(
    specimens_dir,
    resized_trays_coords_dir,
    trays_dir,
    resized_trays_dir,
    guides_dir,
    output_dir,
    config,
    tray_level_dir=None,
):
    """Main entry point. Processes all trays in a drawer."""
    os.makedirs(output_dir, exist_ok=True)

    # Load settings
    settings = config._config.get("traycontext_settings", {})
    bc_threshold = settings.get("bugcleaner_confidence_threshold", 95)
    tc_max_tokens = settings.get("max_tokens", 4000)

    # Get prompts
    tc_prompts = config.prompts.get("traycontext", {})
    system_prompt = tc_prompts.get("system", "")
    user_prompt = tc_prompts.get("user", "")

    # Get model name for tracking
    model_name = config.claude_config.get("model", "")

    if not system_prompt or not user_prompt:
        log("Warning: traycontext prompts not found in config.yaml.")
        return

    # Build bugcleaner runner
    bc_runner = build_model_runner(config, "bugcleaner")

    # Load cached bugcleaner results
    bc_cache_path = os.path.join(output_dir, "bugcleaner_results.csv")
    bc_cache = {}
    if os.path.isfile(bc_cache_path):
        with open(bc_cache_path, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                bc_cache[row["specimen_id"]] = row["has_text"].lower() == "true"
        log(f"  Loaded {len(bc_cache)} cached bugcleaner results")

    # Resumption check
    specimen_csv = os.path.join(output_dir, "specimen_localities.csv")
    done_trays = set()
    if os.path.isfile(specimen_csv):
        with open(specimen_csv, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                done_trays.add(row.get("tray", ""))

    # Discover trays
    coord_files = sorted([
        f for f in os.listdir(resized_trays_coords_dir)
        if f.lower().endswith(".json")
    ])
    log_found("trays", len(coord_files))

    if not coord_files:
        return

    for tray_idx, coord_file in enumerate(coord_files, 1):
        tray_stem = Path(coord_file).stem
        tray_name = tray_stem.replace("_1000", "")

        if tray_name in done_trays or tray_stem in done_trays:
            log(f"  [{tray_idx}/{len(coord_files)}] {tray_name} -- already processed, skipping")
            continue

        log(f"  [{tray_idx}/{len(coord_files)}] Processing tray: {tray_name}")

        # ----- Find specimen crops -----
        all_crops = {}
        for root, _, files in os.walk(specimens_dir):
            for f in sorted(files):
                if f.startswith(tray_name + "_spec_") and not f.startswith("."):
                    spec_id = os.path.splitext(f)[0]
                    all_crops[spec_id] = os.path.join(root, f)

        if not all_crops:
            log(f"    No specimen crop files found for {tray_name}, skipping")
            continue

        # ----- Run bugcleaner (with caching) -----
        text_crops = {}
        notext_specimens = []
        new_bc_results = []
        for spec_id, crop_path in all_crops.items():
            if spec_id in bc_cache:
                has_text = bc_cache[spec_id]
            else:
                has_text = run_bugcleaner_on_crop(crop_path, bc_runner, bc_threshold)
                bc_cache[spec_id] = has_text
                new_bc_results.append({"specimen_id": spec_id, "has_text": str(has_text)})

            if has_text:
                text_crops[spec_id] = crop_path
            else:
                notext_specimens.append(spec_id)

        # Save any new bugcleaner results
        if new_bc_results:
            bc_exists = os.path.isfile(bc_cache_path)
            with open(bc_cache_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["specimen_id", "has_text"])
                if not bc_exists:
                    writer.writeheader()
                writer.writerows(new_bc_results)

        log(f"    Bugcleaner: {len(text_crops)} text / {len(notext_specimens)} no-text")

        if not text_crops:
            log(f"    No text-bearing specimens in {tray_name}, writing empty rows")
            write_outputs(None, tray_name, list(all_crops.keys()), output_dir, model_name)
            continue

        # ----- Find tray image for spatial context -----
        tray_image_path = find_tray_image(resized_trays_dir, tray_name, tray_stem)

        if not tray_image_path:
            log(f"    Warning: no tray image found for {tray_name}, proceeding without")

        # ----- Gather tray header context -----
        context_str, geocode_value = build_tray_context_string(tray_level_dir, tray_name)

        # ----- Call Claude (with batch splitting for large trays) -----
        max_per_batch = settings.get("max_specimens_per_batch", 20)
        include_tray = settings.get("include_tray_image", True)
        spec_ids_list = list(text_crops.keys())

        if len(spec_ids_list) <= max_per_batch:
            # Single call
            log(f"    Sending {len(text_crops)} crops, max_tokens={tc_max_tokens}")
            groups = call_claude_multicrop(
                tray_image_path=tray_image_path,
                specimen_crops=text_crops,
                tray_context_str=context_str,
                api_key=config.api_keys["anthropic"],
                model=config.claude_config["model"],
                max_tokens=tc_max_tokens,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                include_tray_image=include_tray,
            )
        else:
            # Split into batches
            import math
            n_batches = math.ceil(len(spec_ids_list) / max_per_batch)
            log(f"    Splitting {len(spec_ids_list)} crops into {n_batches} batches of ~{max_per_batch}")
            all_groups = []
            group_offset = 0

            for batch_idx in range(n_batches):
                start = batch_idx * max_per_batch
                end = min(start + max_per_batch, len(spec_ids_list))
                batch_ids = spec_ids_list[start:end]
                batch_crops = {sid: text_crops[sid] for sid in batch_ids}

                log(f"    Batch {batch_idx+1}/{n_batches}: {len(batch_crops)} crops, max_tokens={tc_max_tokens}")
                batch_groups = call_claude_multicrop(
                    tray_image_path=tray_image_path,
                    specimen_crops=batch_crops,
                    tray_context_str=context_str,
                    api_key=config.api_keys["anthropic"],
                    model=config.claude_config["model"],
                    max_tokens=tc_max_tokens,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    include_tray_image=include_tray,
                )

                if batch_groups:
                    # Renumber groups to avoid collisions across batches
                    for g in batch_groups:
                        g["label_group"] = g.get("label_group", 0) + group_offset
                    group_offset += len(batch_groups)
                    all_groups.extend(batch_groups)
                else:
                    log(f"    Batch {batch_idx+1} returned unparseable output")

            groups = all_groups if all_groups else None

        if groups is None:
            log(f"    Claude returned unparseable output for {tray_name}")
            write_outputs([], tray_name, notext_specimens, output_dir, model_name)
            continue

        log(f"    Claude returned {len(groups)} label group(s)")

        # ----- Validate -----
        validate_groups(groups, geocode_value)

        # ----- Write outputs -----
        write_outputs(groups, tray_name, notext_specimens, output_dir, model_name)

    log("Tray-context transcription complete.")