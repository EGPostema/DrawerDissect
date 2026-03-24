"""
merge_data.py
-------------
Merges all available data sources (measurements, tray-context localities,
taxonomy, barcodes, geocodes) into comprehensive specimen and tray tables.

Drop this file into functions/, replacing the existing merge_data.py.
"""

import os
import re
import shutil
import pandas as pd
from datetime import datetime


# ===================================================================
# Tray lookup table
# ===================================================================

def generate_tray_lookup(trays_dir, specimens_dir=None, barcode_csv_path=None,
                         geocode_csv_path=None, taxonomy_csv_path=None,
                         labels_dir=None, output_path=None):
    """
    Generate a lookup table of all tray images found in the trays directory.
    Optionally enriches with barcode, geocode, taxonomy, and specimen counts.
    """
    tray_data = []

    for root, _, files in os.walk(trays_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png')):
                tray_id = os.path.splitext(file)[0]
                match = re.match(r'(.+)_tray_\d+', tray_id)
                drawer_id = match.group(1) if match else "MISSING"
                tray_data.append({
                    'drawer_id': drawer_id,
                    'tray_id': tray_id,
                    'tray_filename': file,
                })

    tray_df = pd.DataFrame(tray_data)

    # Count specimens per tray
    if specimens_dir and os.path.exists(specimens_dir):
        spec_counts = {}
        for root, _, files in os.walk(specimens_dir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png')):
                    full_id = os.path.splitext(f)[0]
                    match = re.match(r'(.+_tray_\d+)_spec_', full_id)
                    if match:
                        tid = match.group(1)
                        spec_counts[tid] = spec_counts.get(tid, 0) + 1
        if spec_counts:
            counts_df = pd.DataFrame(list(spec_counts.items()), columns=['tray_id', 'specimen_count'])
            tray_df = pd.merge(tray_df, counts_df, on='tray_id', how='left')
            tray_df['specimen_count'] = tray_df['specimen_count'].fillna(0).astype(int)
        else:
            tray_df['specimen_count'] = 0
    else:
        tray_df['specimen_count'] = 0

    # Collect existing label filenames for detection flags
    existing_labels = set()
    if labels_dir and os.path.exists(labels_dir):
        for root, _, files in os.walk(labels_dir):
            existing_labels.update(files)

    # --- Barcodes ---
    if barcode_csv_path and os.path.exists(barcode_csv_path):
        try:
            barcode_df = pd.read_csv(barcode_csv_path)
            barcode_df['tray_id'] = barcode_df['tray_id'].astype(str)
            tray_df = pd.merge(tray_df, barcode_df[['tray_id', 'unit_barcode']], on='tray_id', how='left')
            tray_df['unit_barcode'] = tray_df['unit_barcode'].fillna("MISSING")
            print(f"Added barcode information from {barcode_csv_path}")

            if labels_dir:
                tray_df['barcode_detect'] = 'not detected'
                for idx, row in tray_df.iterrows():
                    if f"{row['tray_id']}_barcode.jpg" in existing_labels:
                        tray_df.at[idx, 'barcode_detect'] = 'detected'
        except Exception as e:
            print(f"Error loading barcode data: {e}")

    # --- Geocodes ---
    if geocode_csv_path and os.path.exists(geocode_csv_path):
        try:
            geocode_df = pd.read_csv(geocode_csv_path)
            geocode_df['tray_id'] = geocode_df['tray_id'].astype(str)
            tray_df = pd.merge(tray_df, geocode_df[['tray_id', 'geocode']],
                               on='tray_id', how='left')
            tray_df['geocode'] = tray_df['geocode'].fillna("MISSING")
            print(f"Added geocode information from {geocode_csv_path}")

            if labels_dir:
                tray_df['geocode_detect'] = 'not detected'
                for idx, row in tray_df.iterrows():
                    if f"{row['tray_id']}_geocode.jpg" in existing_labels:
                        tray_df.at[idx, 'geocode_detect'] = 'detected'
        except Exception as e:
            print(f"Error loading geocode data: {e}")

    # --- Taxonomy ---
    if taxonomy_csv_path and os.path.exists(taxonomy_csv_path):
        try:
            taxonomy_df = pd.read_csv(taxonomy_csv_path)
            taxonomy_df['tray_id'] = taxonomy_df['tray_id'].astype(str)
            tray_df = pd.merge(tray_df, taxonomy_df[['tray_id', 'taxonomy']].rename(
                columns={'taxonomy': 'full_taxonomy'}), on='tray_id', how='left')
            tray_df['full_taxonomy'] = tray_df['full_taxonomy'].fillna("MISSING")
            print(f"Added taxonomy information from {taxonomy_csv_path}")

            if labels_dir:
                tray_df['taxonomy_detect'] = 'not detected'
                for idx, row in tray_df.iterrows():
                    if f"{row['tray_id']}_label.jpg" in existing_labels:
                        tray_df.at[idx, 'taxonomy_detect'] = 'detected'
        except Exception as e:
            print(f"Error loading taxonomy data: {e}")

    # Reorder columns
    column_order = ['drawer_id', 'tray_id', 'tray_filename']
    for col in ['unit_barcode', 'geocode', 'full_taxonomy',
                'barcode_detect', 'geocode_detect', 'taxonomy_detect',
                'specimen_count', 'masked_specimen_count', 'incomplete_specimen_count']:
        if col in tray_df.columns:
            column_order.append(col)
    tray_df = tray_df[[c for c in column_order if c in tray_df.columns]]

    if output_path and not tray_df.empty:
        tray_df.to_csv(output_path, index=False)
        print(f"Generated tray lookup table with {len(tray_df)} entries saved to {output_path}")

    return tray_df


# ===================================================================
# Specimen table
# ===================================================================

def create_specimen_table(specimens_dir, output_path=None):
    """
    Create the initial specimen-level table from specimen image filenames.
    """
    specimen_data = []

    for root, _, files in os.walk(specimens_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png')):
                full_id = os.path.splitext(file)[0]
                match = re.match(r'(.+)_tray_(\d+)_spec_', full_id)
                if match:
                    drawer_id = match.group(1)
                    tray_num = match.group(2)
                    tray_id = f"{drawer_id}_tray_{tray_num}"
                else:
                    drawer_id = "custom_specimens"
                    tray_id = "custom_specimens"

                specimen_data.append({
                    'spec_filename': file,
                    'full_id': full_id,
                    'drawer_id': drawer_id,
                    'tray_id': tray_id,
                })

    specimen_df = pd.DataFrame(specimen_data)

    if output_path and not specimen_df.empty:
        specimen_df.to_csv(output_path, index=False)
        print(f"Created specimen table with {len(specimen_df)} entries saved to {output_path}")
    elif not specimen_df.empty:
        print(f"Created specimen table with {len(specimen_df)} entries")
    else:
        print("No specimen images found")

    return specimen_df


# ===================================================================
# Measurement data
# ===================================================================

def add_measurement_data(specimen_df, measurements_path, sizeratios_path=None):
    """
    Add measurement data to the specimen table if available.
    Calculates mm measurements when sizeratios.csv is available.
    """
    if not os.path.exists(measurements_path):
        print(f"Measurements file not found at {measurements_path}")
        return specimen_df

    try:
        measurements_df = pd.read_csv(measurements_path)

        measurement_columns = ['full_id', 'len1_px', 'len2_px', 'area_px', 'mask_OK']

        # mm measurements from sizeratios
        if sizeratios_path and os.path.exists(sizeratios_path):
            try:
                ratios_df = pd.read_csv(sizeratios_path)
                if 'tray_id' in ratios_df.columns and 'px_per_mm' in ratios_df.columns:
                    # Extract tray_id from full_id for matching
                    measurements_df['_tray_id'] = measurements_df['full_id'].str.extract(r'(.+_tray_\d+)_spec_')
                    measurements_df = pd.merge(measurements_df, ratios_df[['tray_id', 'px_per_mm']],
                                               left_on='_tray_id', right_on='tray_id', how='left')

                    for px_col, mm_col in [('len1_px', 'len1_mm'), ('len2_px', 'len2_mm'), ('area_px', 'spec_area_mm2')]:
                        if px_col in measurements_df.columns:
                            if 'area' in px_col:
                                measurements_df[mm_col] = measurements_df[px_col] / (measurements_df['px_per_mm'] ** 2)
                            else:
                                measurements_df[mm_col] = measurements_df[px_col] / measurements_df['px_per_mm']
                            measurement_columns.append(mm_col)

                    measurements_df.drop(columns=['_tray_id', 'tray_id', 'px_per_mm'], errors='ignore', inplace=True)
                    print("Calculated mm measurements from sizeratios")
            except Exception as e:
                print(f"Error calculating mm measurements: {e}")
        else:
            print("No sizeratios file provided - pixel measurements only")

        # Convert mask_OK to boolean
        if 'mask_OK' in measurements_df.columns:
            measurements_df['mask_found'] = measurements_df['mask_OK'].apply(lambda x: x == 'Y')
            measurement_columns.remove('mask_OK')
            measurement_columns.append('mask_found')

        for col in measurement_columns:
            if col not in measurements_df.columns:
                measurements_df[col] = None

        measurements_df = measurements_df[[c for c in measurement_columns if c in measurements_df.columns]]

        merged_df = pd.merge(specimen_df, measurements_df, on='full_id', how='left')

        for col in measurement_columns[1:]:
            if col == 'mask_found':
                merged_df[col] = merged_df[col].fillna(False)
            elif col in ['len1_px', 'len2_px', 'area_px', 'len1_mm', 'len2_mm', 'spec_area_mm2']:
                merged_df[col] = merged_df[col].fillna(-1)

        print(f"Added measurement data from {measurements_path}")
        return merged_df

    except Exception as e:
        print(f"Error adding measurement data: {e}")
        return specimen_df


# ===================================================================
# Tray-context locality data (replaces old add_label_transcription)
# ===================================================================

def add_tray_context_data(specimen_df, specimen_localities_path):
    """
    Add tray-context locality data to the specimen table.

    specimen_localities.csv has columns:
      tray, specimen_id, label_group, match_type, verbatim_text,
      country, stateProvince, county, municipality, locality,
      collector, date, flags, model

    We join on specimen_id matching full_id (the filename stem).
    """
    if not os.path.exists(specimen_localities_path):
        print(f"Specimen localities file not found at {specimen_localities_path}")
        return specimen_df

    try:
        try:
            loc_df = pd.read_csv(specimen_localities_path, dtype=str, encoding="utf-8").fillna("")
        except UnicodeDecodeError:
            loc_df = pd.read_csv(specimen_localities_path, dtype=str, encoding="latin-1").fillna("")

        # The join key: specimen_id in the localities CSV should match full_id
        # in the specimen table (filename without extension).
        if 'specimen_id' not in loc_df.columns:
            print("Warning: specimen_localities.csv missing 'specimen_id' column")
            return specimen_df

        # Columns to bring in
        locality_cols = [
            'specimen_id', 'label_group', 'match_type', 'verbatim_text',
            'country', 'stateProvince', 'county', 'municipality', 'locality',
            'collector', 'date', 'flags', 'model',
        ]
        # Only keep columns that actually exist in the CSV
        locality_cols = [c for c in locality_cols if c in loc_df.columns]

        merged_df = pd.merge(
            specimen_df,
            loc_df[locality_cols],
            left_on='full_id',
            right_on='specimen_id',
            how='left',
        )

        # Drop the duplicate join key
        if 'specimen_id' in merged_df.columns:
            merged_df.drop(columns=['specimen_id'], inplace=True)

        # Fill missing locality fields with empty strings (not 'NA')
        for col in locality_cols:
            if col != 'specimen_id' and col in merged_df.columns:
                merged_df[col] = merged_df[col].fillna("")

        print(f"Added tray-context locality data from {specimen_localities_path}")
        return merged_df

    except Exception as e:
        print(f"Error adding tray-context data: {e}")
        return specimen_df


# ===================================================================
# Data completeness flag
# ===================================================================

def add_data_completeness_flag(specimen_df, has_measurements=False, has_taxonomy=False,
                               has_barcodes=False, has_geocodes=False,
                               has_localities=False, has_mm_measurements=False):
    """
    Add a data_complete flag indicating whether all expected data is present.
    """
    df = specimen_df.copy()
    df['data_complete'] = True

    # Measurements
    if has_measurements:
        incomplete = ~df.get('mask_found', pd.Series([True] * len(df)))
        for col in ['len1_px', 'len2_px']:
            if col in df.columns:
                incomplete |= (df[col] == -1)
        if has_mm_measurements:
            for col in ['len1_mm', 'len2_mm', 'spec_area_mm2']:
                if col in df.columns:
                    incomplete |= (df[col] == -1)
        df.loc[incomplete, 'data_complete'] = False

    # Taxonomy
    if has_taxonomy and 'full_taxonomy' in df.columns:
        df.loc[df['full_taxonomy'].isin(["NA", "MISSING", ""]), 'data_complete'] = False

    # Barcodes
    if has_barcodes and 'unit_barcode' in df.columns:
        df.loc[df['unit_barcode'].isin(["NA", "MISSING", ""]), 'data_complete'] = False

    # Geocodes
    if has_geocodes and 'geocode' in df.columns:
        df.loc[df['geocode'].isin(["NA", "MISSING", ""]), 'data_complete'] = False

    # Tray-context localities
    if has_localities and 'country' in df.columns:
        # Mark incomplete if country is empty and match_type isn't no_text_detected
        no_locality = (df['country'] == "") & (df.get('match_type', "") != "no_text_detected")
        df.loc[no_locality, 'data_complete'] = False

    return df


# ===================================================================
# Drawer summary
# ===================================================================

def generate_drawer_summary(tray_df, specimen_df, output_path=None):
    """
    Generate a summary table with metrics aggregated at the drawer level.
    """
    tray_summary = tray_df.groupby('drawer_id').agg({
        'tray_id': 'nunique'
    }).reset_index().rename(columns={'tray_id': 'tray_count'})

    specimen_count = specimen_df.groupby('drawer_id').size().reset_index(name='specimen_count')
    summary_df = pd.merge(tray_summary, specimen_count, on='drawer_id', how='left')
    summary_df['specimen_count'] = summary_df['specimen_count'].fillna(0).astype(int)

    if 'mask_found' in specimen_df.columns:
        masked_counts = (specimen_df[specimen_df['mask_found'] == True]
                         .groupby('drawer_id').size()
                         .reset_index(name='masked_specimen_count'))
        summary_df = pd.merge(summary_df, masked_counts, on='drawer_id', how='left')
        summary_df['masked_specimen_count'] = summary_df['masked_specimen_count'].fillna(0).astype(int)
    else:
        summary_df['masked_specimen_count'] = 0

    if output_path and not summary_df.empty:
        summary_df.to_csv(output_path, index=False)
        print(f"Generated drawer summary with {len(summary_df)} entries saved to {output_path}")

    return summary_df


# ===================================================================
# Main merge function
# ===================================================================

def merge_data(specimens_dir, measurements_path=None, specimen_localities_path=None,
               taxonomy_path=None, unit_barcodes_path=None, geocodes_path=None,
               sizeratios_path=None, labels_dir=None, output_base_path=None):
    """
    Merge all available data sources into comprehensive specimen and tray tables.

    Args:
        specimens_dir:           Directory containing specimen images
        measurements_path:       Path to measurements CSV
        specimen_localities_path: Path to specimen_localities.csv (from tray-context transcription)
        taxonomy_path:           Path to taxonomy CSV
        unit_barcodes_path:      Path to unit barcodes CSV
        geocodes_path:           Path to geocodes CSV
        sizeratios_path:         Path to size ratios CSV
        labels_dir:              Directory containing label images
        output_base_path:        Base path for output files
    """
    try:
        timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M')
        output_folder = f"{output_base_path}_{timestamp}" if output_base_path else f"data_merge_{timestamp}"
        os.makedirs(output_folder, exist_ok=True)

        trays_dir = os.path.join(os.path.dirname(specimens_dir), "trays")

        has_measurements = measurements_path and os.path.exists(measurements_path)
        has_localities = specimen_localities_path and os.path.exists(specimen_localities_path)
        has_taxonomy = taxonomy_path and os.path.exists(taxonomy_path)
        has_barcodes = unit_barcodes_path and os.path.exists(unit_barcodes_path)
        has_geocodes = geocodes_path and os.path.exists(geocodes_path)
        has_mm_measurements = sizeratios_path and os.path.exists(sizeratios_path)

        # --- Tray lookup ---
        tray_lookup_path = os.path.join(output_folder, "trays.csv")
        tray_df = generate_tray_lookup(
            trays_dir=trays_dir,
            specimens_dir=specimens_dir,
            barcode_csv_path=unit_barcodes_path,
            geocode_csv_path=geocodes_path,
            taxonomy_csv_path=taxonomy_path,
            labels_dir=labels_dir,
            output_path=None,
        )

        # --- Specimen table ---
        specimen_path = os.path.join(output_folder, "specimens.csv")
        specimen_df = create_specimen_table(specimens_dir)

        if has_measurements:
            specimen_df = add_measurement_data(specimen_df, measurements_path, sizeratios_path)

        if has_localities:
            specimen_df = add_tray_context_data(specimen_df, specimen_localities_path)

        # Merge tray-level header info onto specimens
        if len(tray_df) > 0 and any(c in tray_df.columns for c in ['unit_barcode', 'geocode', 'full_taxonomy']):
            tray_info_cols = ['tray_id']
            for col in ['unit_barcode', 'geocode', 'full_taxonomy']:
                if col in tray_df.columns:
                    tray_info_cols.append(col)

            specimen_df = pd.merge(specimen_df, tray_df[tray_info_cols], on='tray_id', how='left')
            for col in tray_info_cols[1:]:
                specimen_df[col] = specimen_df[col].fillna("")

        # Completeness flag
        specimen_df = add_data_completeness_flag(
            specimen_df,
            has_measurements=has_measurements,
            has_taxonomy=has_taxonomy,
            has_barcodes=has_barcodes,
            has_geocodes=has_geocodes,
            has_localities=has_localities,
            has_mm_measurements=has_mm_measurements,
        )

        # Incomplete specimen counts on tray table
        if 'data_complete' in specimen_df.columns and len(specimen_df) > 0:
            incomplete_data = (specimen_df[specimen_df['data_complete'] == False]
                               .groupby('tray_id').size()
                               .reset_index(name='incomplete_specimen_count'))
            all_trays = pd.DataFrame({'tray_id': tray_df['tray_id'].unique()})
            incomplete_data = pd.merge(all_trays, incomplete_data, on='tray_id', how='left')
            incomplete_data['incomplete_specimen_count'] = incomplete_data['incomplete_specimen_count'].fillna(0).astype(int)
            tray_df = pd.merge(tray_df, incomplete_data[['tray_id', 'incomplete_specimen_count']],
                               on='tray_id', how='left')
            tray_df['incomplete_specimen_count'] = tray_df['incomplete_specimen_count'].fillna(0).astype(int)
        else:
            tray_df['incomplete_specimen_count'] = 0

        # Masked specimen counts on tray table
        if 'mask_found' in specimen_df.columns and len(specimen_df) > 0:
            masked_data = (specimen_df[specimen_df['mask_found'] == True]
                           .groupby('tray_id').size()
                           .reset_index(name='masked_specimen_count'))
            all_trays = pd.DataFrame({'tray_id': tray_df['tray_id'].unique()})
            masked_data = pd.merge(all_trays, masked_data, on='tray_id', how='left')
            masked_data['masked_specimen_count'] = masked_data['masked_specimen_count'].fillna(0).astype(int)
            tray_df = pd.merge(tray_df, masked_data[['tray_id', 'masked_specimen_count']],
                               on='tray_id', how='left')
            tray_df['masked_specimen_count'] = tray_df['masked_specimen_count'].fillna(0).astype(int)
        else:
            tray_df['masked_specimen_count'] = 0

        # --- Save outputs ---
        tray_df.to_csv(tray_lookup_path, index=False)
        print(f"Saved tray lookup table to {tray_lookup_path}")
        specimen_df.to_csv(specimen_path, index=False)
        print(f"Saved merged specimen data to {specimen_path}")

        summary_path = os.path.join(output_folder, "drawers.csv")
        summary_df = generate_drawer_summary(tray_df, specimen_df, summary_path)

        # Copy input files for reference
        data_inputs_folder = os.path.join(output_folder, "data_inputs")
        os.makedirs(data_inputs_folder, exist_ok=True)

        input_files = {
            'measurements.csv': measurements_path,
            'specimen_localities.csv': specimen_localities_path,
            'taxonomy.csv': taxonomy_path,
            'unit_barcodes.csv': unit_barcodes_path,
            'geocodes.csv': geocodes_path,
            'sizeratios.csv': sizeratios_path,
        }
        for name, path in input_files.items():
            if path and os.path.exists(path):
                shutil.copy2(path, os.path.join(data_inputs_folder, name))
                print(f"Copied {name} to data_inputs folder")

        print(f"Data merge complete. Results saved to {output_folder}")
        return tray_df, specimen_df, summary_df

    except Exception as e:
        print(f"Error in merge_data: {e}")
        raise
