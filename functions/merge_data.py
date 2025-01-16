import os
import pandas as pd
from datetime import datetime

def validate_columns(df, required_cols, dataset_name):
    """
    Validate presence of required columns in a DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame to validate
        required_cols (list): List of required column names
        dataset_name (str): Name of dataset for error reporting
    
    Returns:
        bool: True if all required columns present, False otherwise
    """
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"Error: Missing required columns in {dataset_name}: {missing}")
        return False
    return True

def generate_tray_id(series, column_name):
    """
    Generate tray_id from a series with error handling and validation.
    
    Args:
        series (pd.Series): Input series containing full_id or filename
        column_name (str): Name of column being processed for error messages
    
    Returns:
        pd.Series: Generated tray_id series
    """
    # Try extracting tray_id using primary pattern
    tray_ids = series.str.extract(r'(.*?)_spec')[0]
    
    # Check for failed extractions
    failed_mask = tray_ids.isna()
    if failed_mask.any():
        print(f"Warning: Failed to extract tray_id for {failed_mask.sum()} rows in {column_name}")
        print("Affected values:", series[failed_mask].tolist())
    
    # Validate format
    if not tray_ids.isna().all():  # Only validate if we have some valid tray_ids
        invalid_mask = ~tray_ids.str.match(r'^[\w-]+$', na=False)  # Basic format validation
        if invalid_mask.any():
            print(f"Warning: Invalid tray_id format for {invalid_mask.sum()} rows in {column_name}")
    
    return tray_ids

def verify_merge_results(merged_df, source_df, key_column):
    """
    Verify merge results and check for potential issues.
    
    Args:
        merged_df (pd.DataFrame): Result of merge operation
        source_df (pd.DataFrame): Original DataFrame before merge
        key_column (str): Name of key column used in merge
    
    Returns:
        bool: True if verification passes, False if serious issues found
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

    Parameters:
        measurements_path (str): Path to the measurements CSV file
        location_checked_path (str): Path to the location-checked CSV file
        taxonomy_path (str): Path to the taxonomy CSV file
        unit_barcodes_path (str): Path to the unit barcodes CSV file
        output_base_path (str): Base path for the output file (timestamp will be appended)
        mode (str): Toggle for FMNH or Default pipelines (default is 'FMNH')

    Returns:
        None: Saves the merged dataset as a CSV file
    """
    # Load datasets with error handling
    try:
        measurements = pd.read_csv(measurements_path)
        location_checked = pd.read_csv(location_checked_path)
        taxonomy = pd.read_csv(taxonomy_path) if taxonomy_path else None
        unit_barcodes = pd.read_csv(unit_barcodes_path) if unit_barcodes_path else None
    except Exception as e:
        print(f"Error loading datasets: {e}")
        return

    if mode == "FMNH":
        # Validate required columns for FMNH mode
        required_measurements = ['full_id']
        required_location = ['filename']
        if not all([
            validate_columns(measurements, required_measurements, 'measurements'),
            validate_columns(location_checked, required_location, 'location_checked')
        ]):
            return

        # Generate tray_ids
        measurements['tray_id'] = generate_tray_id(measurements['full_id'], 'measurements.full_id')
        location_checked['tray_id'] = generate_tray_id(location_checked['filename'], 'location_checked.filename')

        # Verify tray_id generation was successful
        if measurements['tray_id'].isna().all() or location_checked['tray_id'].isna().all():
            print("Error: Failed to generate valid tray_ids. Check input data format.")
            return

        # Merge datasets
        merged = measurements.copy()
        
        # Create spec_filename in measurements to match location_checked
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

        # Select and reorder columns
        final_columns = [
            'full_id', 'drawer_id', 'tray_id', 'unit_barcode', 'full_taxonomy',
            'spec_length_mm', 'spec_area_mm2', 'mask_OK', 'bad_size',
            'spec_filename', 'verbatim_text', 'proposed_location', 'validation_status', 'final_location', 'confidence_notes'
        ]

    elif mode == "Default":
        # Validate required files for Default mode
        if not (taxonomy_path or unit_barcodes_path):
            print("Error: Default pipeline requires either taxonomy or unit barcodes!")
            return

        # Create spec_filename and generate tray_id
        measurements['spec_filename'] = measurements['full_id'] + '.jpg'
        measurements['tray_id'] = generate_tray_id(measurements['full_id'], 'measurements.full_id')

        # Merge datasets dynamically
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

        # Select and reorder columns dynamically
        final_columns = [
            'full_id', 'drawer_id', 'tray_id', 'longest_px', 'area_px', 'mask_OK', 
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

    # Verify all final columns exist
    if not all(col in merged.columns for col in final_columns):
        missing_cols = [col for col in final_columns if col not in merged.columns]
        print(f"Error: Missing expected columns in final dataset: {missing_cols}")
        return

    # Select final columns
    try:
        merged = merged[final_columns]
    except KeyError as e:
        print(f"Error selecting final columns: {e}")
        return

    # Handle missing values
    for col in merged.columns:
        if merged[col].dtype in ['float64', 'int64']:
            merged[col] = merged[col].fillna(-1)  # Use -1 for numerical missing values
        else:
            merged[col] = merged[col].fillna('NA')  # Use 'NA' for string missing values

    # Add timestamp to output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file_path = f"{output_base_path}_{timestamp}.csv"

    # Save the final merged CSV
    try:
        merged.to_csv(output_file_path, index=False)
        print(f"Data successfully merged and saved to {output_file_path}")
        print(f"Final dataset shape: {merged.shape}")
    except Exception as e:
        print(f"Error saving merged dataset: {e}")


