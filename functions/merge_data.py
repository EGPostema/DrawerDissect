import os
import pandas as pd
from datetime import datetime

def validate_columns(df, required_cols, dataset_name):
    """
    Validate presence of required columns in a DataFrame.
    """
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"Error: Missing required columns in {dataset_name}: {missing}")
        return False
    return True

def generate_tray_id(series, column_name):
    """
    Generate tray_id from a series with error handling and validation.
    """
    tray_ids = series.str.extract(r'(.*?)_spec')[0]
    failed_mask = tray_ids.isna()
    if failed_mask.any():
        print(f"Warning: Failed to extract tray_id for {failed_mask.sum()} rows in {column_name}")
        print("Affected values:", series[failed_mask].tolist())
    return tray_ids

def verify_merge_results(merged_df, source_df, key_column):
    """
    Verify merge results and check for potential issues.
    """
    if len(merged_df) == 0:
        print("Error: Merge resulted in empty dataset. Check join conditions.")
        return False
    if len(merged_df) < len(source_df):
        print(f"Warning: Merge resulted in fewer rows than source dataset ({len(merged_df)} vs {len(source_df)})")
    duplicates = merged_df[key_column].duplicated()
    if duplicates.any():
        print(f"Warning: Found {duplicates.sum()} duplicate {key_column} values after merging")
        print("Duplicate values:", merged_df[duplicates][key_column].tolist())
    return True

def merge_data(
    measurements_path, location_checked_path, taxonomy_path, unit_barcodes_path, output_base_path, mode="FMNH"
):
    """
    Merges multiple datasets into a single CSV file with specified columns and formats.
    """
    try:
        measurements = pd.read_csv(measurements_path)
        location_checked = pd.read_csv(location_checked_path)
        taxonomy = pd.read_csv(taxonomy_path) if taxonomy_path else None
        unit_barcodes = pd.read_csv(unit_barcodes_path) if unit_barcodes_path else None
    except Exception as e:
        print(f"Error loading datasets: {e}")
        return

    if mode == "FMNH":
        required_measurements = ['full_id', 'len1_mm', 'len2_mm']
        required_location = ['filename']
        if not all([
            validate_columns(measurements, required_measurements, 'measurements'),
            validate_columns(location_checked, required_location, 'location_checked')
        ]):
            return

        measurements['tray_id'] = generate_tray_id(measurements['full_id'], 'measurements.full_id')
        location_checked['tray_id'] = generate_tray_id(location_checked['filename'], 'location_checked.filename')

        merged = measurements.copy()
        merged['spec_filename'] = merged['full_id'] + '.jpg'

        merge_steps = [
            (unit_barcodes, 'tray_id', 'unit_barcodes'),
            (taxonomy[['tray_id', 'taxonomy']].rename(columns={'taxonomy': 'full_taxonomy'}), 'tray_id', 'taxonomy'),
            (location_checked[['filename', 'verbatim_text', 'proposed_location', 'validation_status', 'final_location', 'confidence_notes']]
             .rename(columns={'filename': 'spec_filename'}), 'spec_filename', 'location_checked')
        ]

        for df, key, name in merge_steps:
            if df is not None:
                merged = pd.merge(merged, df, on=key, how='left')
                if not verify_merge_results(merged, measurements, 'full_id'):
                    print(f"Error during merge with {name} dataset")
                    return

        final_columns = [
            'full_id', 'drawer_id', 'tray_id', 'unit_barcode', 'full_taxonomy',
            'len1_mm', 'len2_mm', 'spec_area_mm2', 'len1_px', 'len2_px', 'mask_OK', 'bad_size',
            'spec_filename', 'verbatim_text', 'proposed_location', 'validation_status', 'final_location', 'confidence_notes'
        ]

    elif mode == "Default":
        if not (taxonomy_path or unit_barcodes_path):
            print("Error: Default pipeline requires either taxonomy or unit barcodes!")
            return

        measurements['spec_filename'] = measurements['full_id'] + '.jpg'
        measurements['tray_id'] = generate_tray_id(measurements['full_id'], 'measurements.full_id')

        merged = measurements.copy()
        merge_steps = []

        if unit_barcodes is not None:
            merge_steps.append((unit_barcodes, 'tray_id', 'unit_barcodes'))
        if taxonomy is not None:
            merge_steps.append((taxonomy.rename(columns={'taxonomy': 'full_taxonomy'}), 'tray_id', 'taxonomy'))

        merge_steps.append(
            (location_checked[['filename', 'verbatim_text', 'proposed_location', 'validation_status', 'final_location', 'confidence_notes']]
             .rename(columns={'filename': 'spec_filename'}), 'spec_filename', 'location_checked')
        )

        for df, key, name in merge_steps:
            merged = pd.merge(merged, df, on=key, how='left')
            if not verify_merge_results(merged, measurements, 'full_id'):
                print(f"Error during merge with {name} dataset")
                return

        final_columns = [
            'full_id', 'drawer_id', 'tray_id', 'len1_px', 'len2_px', 'area_px', 'mask_OK',
            'spec_filename', 'verbatim_text', 'proposed_location', 'validation_status',
            'final_location', 'confidence_notes'
        ]
        if taxonomy is not None:
            final_columns.insert(4, 'full_taxonomy')
        if unit_barcodes is not None:
            final_columns.insert(3, 'unit_barcode')

    else:
        print(f"Invalid mode: {mode}. Please choose 'FMNH' or 'Default'.")
        return

    if not all(col in merged.columns for col in final_columns):
        missing_cols = [col for col in final_columns if col not in merged.columns]
        print(f"Error: Missing expected columns in final dataset: {missing_cols}")
        return

    try:
        merged = merged[final_columns]
    except KeyError as e:
        print(f"Error selecting final columns: {e}")
        return

    for col in merged.columns:
        if merged[col].dtype in ['float64', 'int64']:
            merged[col] = merged[col].fillna(-1)
        else:
            merged[col] = merged[col].fillna('NA')

    # Drop duplicates based on `full_id`, keeping the first occurrence
    merged = merged.drop_duplicates(subset='full_id', keep='first')

    timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M')
    output_file_path = f"{output_base_path}_{timestamp}.csv"

    try:
        merged.to_csv(output_file_path, index=False)
        print(f"Data successfully merged and saved to {output_file_path}")
        print(f"Final dataset shape: {merged.shape}")
    except Exception as e:
        print(f"Error saving merged dataset: {e}")


