import pandas as pd
from datetime import datetime

def merge_data(
    measurements_path, location_checked_path, taxonomy_path, unit_barcodes_path, emu_geocodes_path, output_base_path
):
    # Load the datasets
    measurements = pd.read_csv(measurements_path)
    location_checked = pd.read_csv(location_checked_path)
    taxonomy = pd.read_csv(taxonomy_path)
    unit_barcodes = pd.read_csv(unit_barcodes_path)
    emu_geocodes = pd.read_csv(emu_geocodes_path)

    # Step 1: Rename and preprocess columns
    measurements['spec_filename'] = measurements['full_id'] + '.jpg'  # Create spec_filename

    # Step 2: Merge datasets
    merged = measurements.copy()  # Start with measurements as the base

    # Merge with unit_barcodes to get unit_barcode
    merged = pd.merge(merged, unit_barcodes, on='tray_id', how='left')

    # Merge with taxonomy to get full_taxonomy
    merged = pd.merge(
        merged,
        taxonomy[['tray_id', 'taxonomy']].rename(columns={'taxonomy': 'full_taxonomy'}),
        on='tray_id',
        how='left'
    )

    # Merge with emu_geocodes to get geocode
    merged = pd.merge(merged, emu_geocodes, on='unit_barcode', how='left')

    # Merge with location_checked to get validation_status and location
    merged = pd.merge(
        merged,
        location_checked[['filename', 'validation_status', 'final_location']].rename(
            columns={'filename': 'spec_filename', 'final_location': 'location'}
        ),
        on='spec_filename',
        how='left'
    )

    # Step 3: Select and reorder columns
    final_columns = [
        'full_id', 'drawer_id', 'tray_id', 'unit_barcode', 'full_taxonomy', 'geocode',
        'spec_length_mm', 'spec_area_mm2', 'mask_OK', 'missing_size', 'bad_size',
        'spec_filename', 'location', 'validation_status'
    ]
    merged = merged[final_columns]

    # Step 4: Handle missing values with proper dtype management
    for col in merged.columns:
        if merged[col].dtype in ['float64', 'int64']:
            merged[col] = merged[col].fillna(-1)  # Use -1 for numerical missing values
        else:
            merged[col] = merged[col].fillna('NA')  # Use 'NA' for string missing values

    # Step 5: Add timestamp to output filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file_path = f"{output_base_path}_{timestamp}.csv"  # Append timestamp to output_base_path

    # Step 6: Save the final merged CSV
    merged.to_csv(output_file_path, index=False)
    print(f"Data successfully merged and saved to {output_file_path}")

