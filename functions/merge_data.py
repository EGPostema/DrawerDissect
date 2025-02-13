import os
import shutil
import pandas as pd
from datetime import datetime

def validate_columns(df, required_cols, dataset_name):
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"Missing columns in {dataset_name}: {missing}")
        return False
    return True

def generate_tray_id(series, column_name):
    tray_ids = series.str.extract(r'(.*?)_spec')[0]
    failed_mask = tray_ids.isna()
    if failed_mask.any():
        print(f"Error extracting tray_id for {failed_mask.sum()} rows in {column_name}")
    return tray_ids

def verify_merge_results(merged_df, source_df, key_column):
    if len(merged_df) == 0:
        print("Merge resulted in empty dataset")
        return False
    if len(merged_df) < len(source_df):
        print(f"Merge dropped rows ({len(merged_df)} vs {len(source_df)})")
    duplicates = merged_df[key_column].duplicated()
    if duplicates.any():
        print(f"Found {duplicates.sum()} duplicate {key_column} values")
    return True

def extract_first_genus(taxonomy):
    """Extract the first genus from a full taxonomy string."""
    if pd.isna(taxonomy):
        return 'Unknown'
    return taxonomy.split()[0]

def generate_data_summary(merged_df):
    """
    Generate a summary DataFrame with metrics per drawer_id
    
    Metrics include:
    - Number of trays
    - Number of specimens
    - Proportion of masked specimens
    - Proportion of bad-sized specimens
    - Number of unique genera
    - List of unique genera
    - Proportion of locations verified
    """
    # Group by drawer_id and aggregate metrics
    summary = merged_df.groupby('drawer_id').agg({
        'tray_id': 'nunique',  # Number of unique trays
        # Use len instead of nunique to get total specimens
        'full_id': 'count',  # Total number of specimens
        'mask_OK': lambda x: (x == 'Y').mean(),  # Proportion of masked specimens
        'bad_size': lambda x: (x == 'Y').mean(),  # Proportion of bad-sized specimens
    }).reset_index()

    # Add genera metrics
    summary['unique_genera'] = merged_df.groupby('drawer_id')['full_taxonomy'].apply(
        lambda x: len(set(x.apply(extract_first_genus)))
    ).values

    # Generate alphabetical, comma-separated list of unique genera
    summary['genera_list'] = merged_df.groupby('drawer_id')['full_taxonomy'].apply(
        lambda x: ', '.join(sorted(set(x.apply(extract_first_genus))))
    ).values

    # Proportion of verified locations
    summary['prop_locations_verif'] = merged_df.groupby('drawer_id')['validation_status'].apply(
        lambda x: (x == 'VERIFIED').mean()
    ).values

    # Rename columns for clarity
    summary.columns = [
        'drawer_id', 
        'tray_count', 
        'specimen_count', 
        'prop_masked', 
        'prop_badsize', 
        'unique_genera', 
        'genera_list', 
        'prop_locations_verif'
    ]

    return summary

def merge_data(measurements_path, location_checked_path, taxonomy_path, unit_barcodes_path, output_base_path, mode="FMNH"):
    try:
        # Create timestamped output folder
        timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M')
        output_folder = f"{output_base_path}_{timestamp}"
        os.makedirs(output_folder, exist_ok=True)

        # Copy input files to the output folder
        input_files = [
            measurements_path, 
            location_checked_path, 
            taxonomy_path, 
            unit_barcodes_path
        ]
        input_file_names = [
            'measurements.csv', 
            'location_checked.csv', 
            'taxonomy.csv', 
            'unit_barcodes.csv'
        ]
        
        for path, name in zip(input_files, input_file_names):
            if path and os.path.exists(path):
                shutil.copy2(path, os.path.join(output_folder, name))

        # Load datasets
        measurements = pd.read_csv(measurements_path)
        location_checked = pd.read_csv(location_checked_path)
        taxonomy = pd.read_csv(taxonomy_path) if taxonomy_path else None
        unit_barcodes = pd.read_csv(unit_barcodes_path) if unit_barcodes_path else None

        if mode == "FMNH":
            required_measurements = ['full_id', 'len1_mm', 'len2_mm']
            required_location = ['filename']
            if not all([
                validate_columns(measurements, required_measurements, 'measurements'),
                validate_columns(location_checked, required_location, 'location_checked')
            ]):
                return

            # Generate and ensure consistent tray_id types
            measurements['tray_id'] = generate_tray_id(measurements['full_id'], 'measurements.full_id')
            location_checked['tray_id'] = generate_tray_id(location_checked['filename'], 'location_checked.filename')
            
            # Convert tray_id to string in all dataframes
            measurements['tray_id'] = measurements['tray_id'].astype(str)
            location_checked['tray_id'] = location_checked['tray_id'].astype(str)
            if taxonomy is not None:
                taxonomy['tray_id'] = taxonomy['tray_id'].astype(str)
            if unit_barcodes is not None:
                unit_barcodes['tray_id'] = unit_barcodes['tray_id'].astype(str)

            merged = measurements.copy()
            merged['spec_filename'] = merged['full_id'] + '.jpg'

            merge_steps = []
            if unit_barcodes is not None:
                merge_steps.append((unit_barcodes, 'tray_id', 'unit_barcodes'))
            if taxonomy is not None:
                merge_steps.append((
                    taxonomy[['tray_id', 'taxonomy']].rename(columns={'taxonomy': 'full_taxonomy'}),
                    'tray_id', 'taxonomy'
                ))
            merge_steps.append((
                location_checked[['filename', 'verbatim_text', 'proposed_location', 
                                'validation_status', 'final_location', 'confidence_notes']]
                .rename(columns={'filename': 'spec_filename'}),
                'spec_filename', 'location_checked'
            ))

            for df, key, name in merge_steps:
                if df is not None:
                    merged = pd.merge(merged, df, on=key, how='left')
                    if not verify_merge_results(merged, measurements, 'full_id'):
                        print(f"Merge warning: {name} dataset")

            final_columns = [
                'full_id', 'drawer_id', 'tray_id', 'unit_barcode', 'full_taxonomy',
                'len1_mm', 'len2_mm', 'spec_area_mm2', 'len1_px', 'len2_px', 'mask_OK', 'bad_size',
                'spec_filename', 'verbatim_text', 'proposed_location', 'validation_status', 
                'final_location', 'confidence_notes'
            ]

        else:
            print("Error: Only FMNH mode is supported")
            return

        # Verify final columns
        missing_cols = [col for col in final_columns if col not in merged.columns]
        if missing_cols:
            print(f"Missing columns in final dataset: {missing_cols}")
            print("Available columns:", sorted(merged.columns.tolist()))
            return

        # Clean and save
        merged = merged[final_columns]
        for col in merged.columns:
            if merged[col].dtype in ['float64', 'int64']:
                merged[col] = merged[col].fillna(-1)
            else:
                merged[col] = merged[col].fillna('NA')

        merged = merged.drop_duplicates(subset='full_id', keep='first')
        
        # Save merged data to the timestamped folder
        merged_data_path = os.path.join(output_folder, 'merged_data.csv')
        merged.to_csv(merged_data_path, index=False)
        
        # Generate and save summary
        summary = generate_data_summary(merged)
        summary_path = os.path.join(output_folder, 'data_summary.csv')
        summary.to_csv(summary_path, index=False)
        
        # Print first 5 rows with ellipsis
        print(summary.head())
        if len(summary) > 5:
            print("...")
        
        return merged, summary
        
    except Exception as e:
        print(f"Error in merge_data: {str(e)}")
        raise


