import os
import pandas as pd
from datetime import datetime

def merge_data(
    measurements_path, location_checked_path, taxonomy_path, unit_barcodes_path, output_base_path
):
    """
    Merges multiple datasets into a single CSV file with specified columns and formats.

    Parameters:
        measurements_path (str): Path to the measurements CSV file.
        location_checked_path (str): Path to the location-checked CSV file.
        taxonomy_path (str): Path to the taxonomy CSV file.
        unit_barcodes_path (str): Path to the unit barcodes CSV file.
        output_base_path (str): Base path for the output file (timestamp will be appended).

    Returns:
        None: Saves the merged dataset as a CSV file.
    """
    try:
        measurements = pd.read_csv(measurements_path)
        location_checked = pd.read_csv(location_checked_path)
        taxonomy = pd.read_csv(taxonomy_path)
        unit_barcodes = pd.read_csv(unit_barcodes_path)
    except Exception as e:
        print(f"Error loading datasets: {e}")
        return

    # Validate required columns in measurements
    required_columns = ['tray_id', 'full_id']
    missing_columns = [col for col in required_columns if col not in measurements.columns]
    if missing_columns:
        print(f"Missing columns in measurements: {missing_columns}")
        return

    # Create 'spec_filename'
    measurements['spec_filename'] = measurements['full_id'] + '.jpg'

    # Merge datasets
    merged = measurements.copy()
    merge_steps = [
        (unit_barcodes, 'tray_id'),
        (taxonomy[['tray_id', 'taxonomy']].rename(columns={'taxonomy': 'full_taxonomy'}), 'tray_id'),
        (location_checked[['filename', 'validation_status', 'final_location']]
         .rename(columns={'filename': 'spec_filename', 'final_location': 'location'}), 'spec_filename')
    ]
    for df, key in merge_steps:
        merged = pd.merge(merged, df, on=key, how='left')

    # Select and reorder columns
    final_columns = [
        'full_id', 'drawer_id', 'tray_id', 'unit_barcode', 'full_taxonomy',
        'spec_length_mm', 'spec_area_mm2', 'mask_OK', 'missing_size', 'bad_size',
        'spec_filename', 'location', 'validation_status'
    ]
    merged = merged[final_columns]

    # Handle missing values
    for col in merged.columns:
        if merged[col].dtype in ['float64', 'int64']:
            merged[col] = merged[col].fillna(-1)  # Use -1 for numerical missing values
        else:
            merged[col] = merged[col].fillna('NA')  # Use 'NA' for string missing values

    # Add timestamp to output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file_path = f"{output_base_path}_{timestamp}.csv"  # Append timestamp to output_base_path

    # Save the final merged CSV
    merged.to_csv(output_file_path, index=False)
    print(f"Data successfully merged and saved to {output_file_path}")
