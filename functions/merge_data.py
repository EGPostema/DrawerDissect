import os
import shutil
import pandas as pd
from datetime import datetime

def generate_tray_lookup(trays_dir, specimens_dir=None, barcode_csv_path=None, geocode_csv_path=None, taxonomy_csv_path=None, labels_dir=None, output_path=None):
    """
    Generate a lookup table of all tray images found in the trays directory.
    Optionally enriches with barcode, taxonomy information, and specimen counts.
    
    Args:
        trays_dir (str): Directory containing tray images in nested structure
        specimens_dir (str, optional): Directory containing specimen images
        barcode_csv_path (str, optional): Path to the barcode CSV file
        taxonomy_csv_path (str, optional): Path to the taxonomy CSV file
        labels_dir (str, optional): Path to the labels directory with cropped images
        output_path (str, optional): Path to save the resulting CSV
    
    Returns:
        pd.DataFrame: DataFrame containing tray lookup information
    """
    import os
    import pandas as pd
    import re
    
    # List to store tray information
    tray_data = []
    
    # Walk through the trays directory recursively
    for root, _, files in os.walk(trays_dir):
        for file in files:
            # Check if file is an image
            if file.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png')):
                # Extract tray_id from filename (remove extension)
                tray_id = os.path.splitext(file)[0]
                
                # Extract drawer_id from tray_id pattern {drawer_id}_tray_XX
                match = re.match(r'(.+)_tray_\d+', tray_id)
                if match:
                    drawer_id = match.group(1)
                else:
                    # If pattern doesn't match, mark as MISSING
                    drawer_id = "MISSING"
                
                # Add to tray data
                tray_data.append({
                    'drawer_id': drawer_id,
                    'tray_id': tray_id,
                    'tray_filename': file
                })
    
    # Create DataFrame
    tray_df = pd.DataFrame(tray_data)
    
    # Create a set of all image filenames in the labels directory (if provided)
    existing_labels = set()
    if labels_dir and os.path.exists(labels_dir):
        for root, _, files in os.walk(labels_dir):
            for file in files:
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                    existing_labels.add(file)
        print(f"Found {len(existing_labels)} label images in {labels_dir}")
    
    # Count specimen images for each tray if specimens directory is provided
    if specimens_dir and os.path.exists(specimens_dir):
        # Initialize specimen counts
        tray_df['specimen_count'] = 0
        
        # Create a mapping from tray_id to specimen counts
        specimen_counts = {}
        
        # Walk through the specimens directory
        for root, _, files in os.walk(specimens_dir):
            # Filter for image files
            image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png'))]
            
            if image_files:
                # Extract tray information from the first file
                sample_file = image_files[0]
                match = re.match(r'(.+)_tray_(\d+)_spec_', sample_file)
                if match:
                    drawer_id = match.group(1)
                    tray_num = match.group(2)
                    tray_id = f"{drawer_id}_tray_{tray_num}"
                    
                    # Store the count for this tray
                    specimen_counts[tray_id] = len(image_files)
        
        # Update specimen counts in the DataFrame
        for idx, row in tray_df.iterrows():
            tray_id = row['tray_id']
            if tray_id in specimen_counts:
                tray_df.at[idx, 'specimen_count'] = specimen_counts[tray_id]
                
        print(f"Added specimen counts from {specimens_dir}")
    
    # Load barcode data if path is provided and file exists
    if barcode_csv_path and os.path.exists(barcode_csv_path):
        try:
            barcode_df = pd.read_csv(barcode_csv_path)
            # Ensure tray_id is treated as string in both dataframes
            barcode_df['tray_id'] = barcode_df['tray_id'].astype(str)
            tray_df['tray_id'] = tray_df['tray_id'].astype(str)
            # Merge with tray data
            tray_df = pd.merge(tray_df, barcode_df[['tray_id', 'unit_barcode']], 
                              on='tray_id', how='left')
            # Fill missing barcodes with "MISSING"
            tray_df['unit_barcode'] = tray_df['unit_barcode'].fillna("MISSING")
            print(f"Added barcode information from {barcode_csv_path}")
            
            # Add barcode detection flag if labels directory is provided
            if labels_dir and os.path.exists(labels_dir):
                tray_df['barcode_detect'] = 'not detected'
                for idx, row in tray_df.iterrows():
                    barcode_filename = f"{row['tray_id']}_barcode.jpg"
                    if barcode_filename in existing_labels:
                        tray_df.at[idx, 'barcode_detect'] = 'detected'
                print("Added barcode detection flags")
        except Exception as e:
            print(f"Error loading barcode data: {str(e)}")

    # Load geocode data if path is provided and file exists
    if geocode_csv_path and os.path.exists(geocode_csv_path):
        try:
            geocode_df = pd.read_csv(geocode_csv_path)
            # Ensure tray_id is treated as string in both dataframes
            geocode_df['tray_id'] = geocode_df['tray_id'].astype(str)
            tray_df['tray_id'] = tray_df['tray_id'].astype(str)
            # Merge with tray data
            tray_df = pd.merge(tray_df, geocode_df[['tray_id', 'geocode']], 
                              on='tray_id', how='left')
            # Fill missing geocodes with "MISSING"
            tray_df['geocode'] = tray_df['geocode'].fillna("MISSING")
            print(f"Added geocode information from {geocode_csv_path}")
            
            # Add geocode detection flag if labels directory is provided
            if labels_dir and os.path.exists(labels_dir):
                tray_df['geocode_detect'] = 'not detected'
                for idx, row in tray_df.iterrows():
                    geocode_filename = f"{row['tray_id']}_geocode.jpg"
                    if geocode_filename in existing_labels:
                        tray_df.at[idx, 'geocode_detect'] = 'detected'
                print("Added geocode detection flags")
        except Exception as e:
            print(f"Error loading geocode data: {str(e)}")
    
    # Load taxonomy data if path is provided and file exists
    if taxonomy_csv_path and os.path.exists(taxonomy_csv_path):
        try:
            taxonomy_df = pd.read_csv(taxonomy_csv_path)
            # Ensure tray_id is treated as string in both dataframes
            taxonomy_df['tray_id'] = taxonomy_df['tray_id'].astype(str)
            # Merge with tray data
            tray_df = pd.merge(tray_df, 
                              taxonomy_df[['tray_id', 'taxonomy']].rename(
                                  columns={'taxonomy': 'full_taxonomy'}), 
                              on='tray_id', how='left')
            # Fill missing taxonomy with "MISSING"
            tray_df['full_taxonomy'] = tray_df['full_taxonomy'].fillna("MISSING")
            print(f"Added taxonomy information from {taxonomy_csv_path}")
            
            # Add taxonomy detection flag if labels directory is provided
            if labels_dir and os.path.exists(labels_dir):
                tray_df['taxonomy_detect'] = 'not detected'
                for idx, row in tray_df.iterrows():
                    taxonomy_filename = f"{row['tray_id']}_label.jpg"
                    if taxonomy_filename in existing_labels:
                        tray_df.at[idx, 'taxonomy_detect'] = 'detected'
                print("Added taxonomy detection flags")
        except Exception as e:
            print(f"Error loading taxonomy data: {str(e)}")
    
    # Rearrange columns in the specified order
    # Only include columns that exist in the DataFrame
    column_order = ['drawer_id', 'tray_id', 'tray_filename']
    
    if 'unit_barcode' in tray_df.columns:
        column_order.append('unit_barcode')
    
    if 'geocode' in tray_df.columns:
        column_order.append('geocode')
    
    if 'full_taxonomy' in tray_df.columns:
        column_order.append('full_taxonomy')
    
    if 'barcode_detect' in tray_df.columns:
        column_order.append('barcode_detect')
    
    if 'geocode_detect' in tray_df.columns:
        column_order.append('geocode_detect')
    
    if 'taxonomy_detect' in tray_df.columns:
        column_order.append('taxonomy_detect')
    
    if 'specimen_count' in tray_df.columns:
        column_order.append('specimen_count')
        
    if 'masked_specimen_count' in tray_df.columns:
        column_order.append('masked_specimen_count')
        
    if 'incomplete_specimen_count' in tray_df.columns:
        column_order.append('incomplete_specimen_count')
    
    # Reorder columns
    tray_df = tray_df[column_order]
    
    # Save to CSV if output path is provided
    if output_path and not tray_df.empty:
        tray_df.to_csv(output_path, index=False)
        print(f"Generated tray lookup table with {len(tray_df)} entries saved to {output_path}")
    elif not tray_df.empty:
        print(f"Generated tray lookup table with {len(tray_df)} entries (not saved)")
    else:
        print("No tray images found")
    
    return tray_df

def create_specimen_table(specimens_dir, output_path=None):
    """
    Create the initial specimen-level table based on all specimen image filenames.
    Handles both standard naming (drawer_id_tray_XX_spec_YY) and custom filenames.
    
    Args:
        specimens_dir (str): Directory containing specimen images
        output_path (str, optional): Path to save the resulting CSV
        
    Returns:
        pd.DataFrame: DataFrame with one row per specimen
    """
    import os
    import pandas as pd
    import re
    
    # List to store specimen information
    specimen_data = []
    
    # Walk through the specimens directory recursively
    for root, _, files in os.walk(specimens_dir):
        for file in files:
            # Check if file is an image
            if file.lower().endswith(('.jpg', '.jpeg', '.tif', '.tiff', '.png')):
                # Extract full_id (filename without extension)
                full_id = os.path.splitext(file)[0]
                
                # Try to extract drawer_id and tray_id using standard regex pattern
                match = re.match(r'(.+)_tray_(\d+)_spec_', full_id)
                if match:
                    # Standard naming pattern
                    drawer_id = match.group(1)
                    tray_num = match.group(2)
                    tray_id = f"{drawer_id}_tray_{tray_num}"
                else:
                    # Custom naming - use generic identifiers
                    drawer_id = "custom_specimens"
                    tray_id = "custom_specimens"
                
                # Add to specimen data
                specimen_data.append({
                    'spec_filename': file,
                    'full_id': full_id,
                    'drawer_id': drawer_id,
                    'tray_id': tray_id
                })
    
    # Create DataFrame
    specimen_df = pd.DataFrame(specimen_data)
    
    # Save to CSV if output path is provided
    if output_path and not specimen_df.empty:
        specimen_df.to_csv(output_path, index=False)
        print(f"Created specimen table with {len(specimen_df)} entries saved to {output_path}")
    elif not specimen_df.empty:
        print(f"Created specimen table with {len(specimen_df)} entries (not saved)")
    else:
        print("No specimen images found")
    
    return specimen_df

def add_measurement_data(specimen_df, measurements_path, sizeratios_path=None):
    """
    Add measurement data to the specimen table if available.
    Calculates mm measurements when sizeratios.csv is available.
    
    Args:
        specimen_df (pd.DataFrame): DataFrame containing specimen information
        measurements_path (str): Path to the measurements CSV file
        sizeratios_path (str, optional): Path to the sizeratios CSV file for px to mm conversion
        
    Returns:
        pd.DataFrame: Enhanced DataFrame with measurement information
    """
    import os
    import pandas as pd
    
    if not os.path.exists(measurements_path):
        print(f"Measurements file not found at {measurements_path}")
        return specimen_df
    
    try:
        # Load measurements data
        measurements_df = pd.read_csv(measurements_path)
        
        # Basic measurement columns (always included)
        measurement_columns = ['full_id', 'len1_px', 'len2_px', 'area_px', 'mask_OK']
        
        # Check for required columns in the measurements file
        for col in ['full_id', 'len1_px', 'len2_px', 'area_px']:
            if col not in measurements_df.columns:
                print(f"Warning: Required column '{col}' not found in measurements file")
                return specimen_df
        
        # Check if sizeratios.csv exists
        has_sizeratios = sizeratios_path and os.path.exists(sizeratios_path)
        
        # If sizeratios.csv exists, calculate mm measurements
        if has_sizeratios:
            print(f"Found sizeratios file at {sizeratios_path}, will calculate mm measurements")
            try:
                # Load sizeratios data
                sizeratios_df = pd.read_csv(sizeratios_path)
                
                # Check if required columns exist in sizeratios.csv
                if 'drawer_id' not in sizeratios_df.columns or 'px_mm_ratio' not in sizeratios_df.columns:
                    print("Warning: sizeratios.csv missing required columns (drawer_id, px_mm_ratio)")
                    return specimen_df
                
                # Create a mapping of drawer_id to px_mm_ratio
                sizeratios_map = sizeratios_df.set_index('drawer_id')['px_mm_ratio'].to_dict()
                
                # Extract drawer_id from full_id in measurements_df if needed
                if 'drawer_id' not in measurements_df.columns:
                    print("Adding drawer_id to measurements data")
                    measurements_df['drawer_id'] = measurements_df['full_id'].apply(
                        lambda x: x.split('_tray_')[0] if '_tray_' in x else None
                    )
                
                # Match px_mm_ratio to each specimen based on drawer_id
                measurements_df['px_mm_ratio'] = measurements_df['drawer_id'].map(sizeratios_map)
                
                # Calculate mm measurements for specimens with a valid ratio
                measurements_df['len1_mm'] = measurements_df.apply(
                    lambda row: row['len1_px'] / row['px_mm_ratio'] if pd.notnull(row['px_mm_ratio']) else None, 
                    axis=1
                )
                
                measurements_df['len2_mm'] = measurements_df.apply(
                    lambda row: row['len2_px'] / row['px_mm_ratio'] if pd.notnull(row['px_mm_ratio']) else None, 
                    axis=1
                )
                
                measurements_df['spec_area_mm2'] = measurements_df.apply(
                    lambda row: row['area_px'] / (row['px_mm_ratio'] ** 2) if pd.notnull(row['px_mm_ratio']) else None, 
                    axis=1
                )
                
                # Add mm columns to our list of columns to include
                measurement_columns.extend(['len1_mm', 'len2_mm', 'spec_area_mm2', 'px_mm_ratio'])
                    
            except Exception as e:
                print(f"Error calculating mm measurements: {str(e)}")
        else:
            print("No sizeratios file provided - pixel measurements only")
        
        # Convert mask_OK to a mask_found boolean flag
        if 'mask_OK' in measurements_df.columns:
            measurements_df['mask_found'] = measurements_df['mask_OK'].apply(
                lambda x: True if x == 'Y' else False
            )
            measurement_columns.remove('mask_OK')
            measurement_columns.append('mask_found')
        
        # Select only the columns we need
        for col in measurement_columns:
            if col not in measurements_df.columns:
                measurements_df[col] = None
                
        measurements_df = measurements_df[[col for col in measurement_columns if col in measurements_df.columns]]
        
        # Merge with specimen data
        merged_df = pd.merge(specimen_df, measurements_df, on='full_id', how='left')
        
        # Fill missing values with appropriate defaults
        for col in measurement_columns[1:]:  # Skip full_id
            if col == 'mask_found':
                merged_df[col] = merged_df[col].fillna(False)
            elif col in ['len1_px', 'len2_px', 'area_px']:
                merged_df[col] = merged_df[col].fillna(-1)
            elif col in ['len1_mm', 'len2_mm', 'spec_area_mm2']:
                merged_df[col] = merged_df[col].fillna(-1)
        
        print(f"Added measurement data from {measurements_path}")
        return merged_df
        
    except Exception as e:
        print(f"Error adding measurement data: {str(e)}")
        return specimen_df

def add_label_transcription(specimen_df, location_checked_path):
    """
    Add label transcription and location data to the specimen table if available.
    
    Args:
        specimen_df (pd.DataFrame): DataFrame containing specimen information
        location_checked_path (str): Path to the location_checked CSV file
        
    Returns:
        pd.DataFrame: Enhanced DataFrame with transcription information
    """
    import os
    import pandas as pd
    
    if not os.path.exists(location_checked_path):
        print(f"Location checked file not found at {location_checked_path}")
        return specimen_df
    
    try:
        # Load location checked data
        location_df = pd.read_csv(location_checked_path)
        
        expected_cols = {
            'filename': 'spec_filename',
            'verbatim_text': 'verbatim_text',
            'proposed_location': 'proposed_location',
            'validation_status': 'validation_status',
            'final_location': 'final_location'
        }

        # Rename only if present
        location_df = location_df.rename(columns={k: v for k, v in expected_cols.items() if k in location_df.columns})

        # Ensure all required columns exist
        for new_col in expected_cols.values():
            if new_col not in location_df.columns:
                print(f"Warning: Column '{new_col}' missing from location_checked.csv — filling with 'NA'")
                location_df[new_col] = "NA"

        # Proceed with merge
        merged_df = pd.merge(specimen_df, location_df[list(expected_cols.values())], on='spec_filename', how='left')

        # Fill missing values
        for col in list(expected_cols.values())[1:]:
            merged_df[col] = merged_df[col].fillna("NA")

        print(f"Added label transcription data from {location_checked_path}")
        return merged_df

    except Exception as e:
        print(f"Error adding label transcription data: {str(e)}")
        return specimen_df

def add_data_completeness_flag(specimen_df, has_measurements=False, has_taxonomy=False, 
                         has_barcodes=False, has_geocodes=False, has_locations=False, has_mm_measurements=False):
    """
    Add a data_complete flag to the specimen DataFrame indicating whether
    all expected data for a specimen is available.
    
    Args:
        specimen_df (pd.DataFrame): DataFrame containing specimen information
        has_measurements (bool): Whether measurement data was added
        has_taxonomy (bool): Whether taxonomy data was added
        has_barcodes (bool): Whether barcode data was added
        has_geocodes (bool): Whether geocode data was added
        has_locations (bool): Whether location data was added
        has_mm_measurements (bool): Whether mm measurements are available
        
    Returns:
        pd.DataFrame: Enhanced DataFrame with data_complete flag
    """
    # Create a copy to avoid modifying the original
    df = specimen_df.copy()
    
    # Initialize data_complete as True for all specimens
    df['data_complete'] = True
    
    # Check measurement completeness if applicable
    if has_measurements:
        # Check base measurement completeness (always check px measurements and mask)
        measurement_incomplete = (~df['mask_found'])  # Mask must exist
        
        # Check pixel measurements if they exist
        if 'len1_px' in df.columns:
            measurement_incomplete |= (df['len1_px'] == -1)
        if 'len2_px' in df.columns:
            measurement_incomplete |= (df['len2_px'] == -1)
        
        # Only check mm measurements if they're available and expected
        if has_mm_measurements:
            if 'len1_mm' in df.columns:
                measurement_incomplete |= (df['len1_mm'] == -1)
            if 'len2_mm' in df.columns:
                measurement_incomplete |= (df['len2_mm'] == -1)
            if 'spec_area_mm2' in df.columns:
                measurement_incomplete |= (df['spec_area_mm2'] == -1)
                
        df.loc[measurement_incomplete, 'data_complete'] = False
    
    # Check taxonomy completeness if applicable
    if has_taxonomy and 'full_taxonomy' in df.columns:
        taxonomy_incomplete = (
            (df['full_taxonomy'] == "NA") | 
            (df['full_taxonomy'] == "MISSING")
        )
        df.loc[taxonomy_incomplete, 'data_complete'] = False
    
    # Check barcode completeness if applicable
    if has_barcodes and 'unit_barcode' in df.columns:
        barcode_incomplete = (
            (df['unit_barcode'] == "NA") | 
            (df['unit_barcode'] == "MISSING")
        )
        df.loc[barcode_incomplete, 'data_complete'] = False

    # Check geocode completeness if applicable
    if has_geocodes and 'geocode' in df.columns:
        geocode_incomplete = (
            (df['geocode'] == "NA") | 
            (df['geocode'] == "MISSING")
        )
        df.loc[geocode_incomplete, 'data_complete'] = False
    
    # Check location completeness if applicable
    if has_locations and 'validation_status' in df.columns:
        location_incomplete = (
            (df['verbatim_text'] == "MISSING") |
            (df['final_location'] == "MISSING")
        )
        df.loc[location_incomplete, 'data_complete'] = False
    
    return df

def generate_drawer_summary(tray_df, specimen_df, output_path=None):
    """
    Generate a simplified summary table with metrics aggregated at the drawer level.
    
    Args:
        tray_df (pd.DataFrame): Tray lookup table
        specimen_df (pd.DataFrame): Specimen-level merged data
        output_path (str, optional): Path to save the resulting CSV
        
    Returns:
        pd.DataFrame: Summary DataFrame with one row per drawer
    """
    import pandas as pd
    
    # Group trays by drawer_id and count unique trays
    tray_summary = tray_df.groupby('drawer_id').agg({
        'tray_id': 'nunique'  # Count of unique trays per drawer
    }).reset_index()
    
    # Rename column for clarity
    tray_summary = tray_summary.rename(columns={
        'tray_id': 'tray_count'
    })
    
    # Get specimen count from specimen_df
    specimen_count = specimen_df.groupby('drawer_id').size().reset_index(name='specimen_count')
    
    # Merge tray_summary with specimen_count
    summary_df = pd.merge(tray_summary, specimen_count, on='drawer_id', how='left')
    summary_df['specimen_count'] = summary_df['specimen_count'].fillna(0).astype(int)
    
    # Calculate masked specimen count if mask column exists
    if 'mask_found' in specimen_df.columns:
        # Count specimens with mask_found=True for each drawer
        masked_counts = specimen_df[specimen_df['mask_found'] == True].groupby('drawer_id').size().reset_index(name='masked_specimen_count')
        summary_df = pd.merge(summary_df, masked_counts, on='drawer_id', how='left')
        summary_df['masked_specimen_count'] = summary_df['masked_specimen_count'].fillna(0).astype(int)
    else:
        summary_df['masked_specimen_count'] = 0
    
    # Save to CSV if output path is provided
    if output_path and not summary_df.empty:
        summary_df.to_csv(output_path, index=False)
        print(f"Generated drawer summary with {len(summary_df)} entries saved to {output_path}")
    
    return summary_df

def merge_data(specimens_dir, measurements_path=None, location_checked_path=None, 
              taxonomy_path=None, unit_barcodes_path=None, geocodes_path=None, sizeratios_path=None,
              labels_dir=None, output_base_path=None):
    """
    Merge all available data sources into comprehensive specimen and tray tables.
    
    Args:
        specimens_dir: Directory containing specimen images
        measurements_path: Path to measurements CSV
        location_checked_path: Path to location validation CSV
        taxonomy_path: Path to taxonomy CSV
        unit_barcodes_path: Path to unit barcodes CSV
        geocodes_path: Path to geocodes CSV
        sizeratios_path: Path to size ratios CSV
        labels_dir: Directory containing label images
        output_base_path: Base path for output files
    """
    try:
        # Create timestamped output folder
        timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M')
        output_folder = f"{output_base_path}_{timestamp}" if output_base_path else f"data_merge_{timestamp}"
        os.makedirs(output_folder, exist_ok=True)

        trays_dir = os.path.join(os.path.dirname(specimens_dir), "trays")

        has_measurements = measurements_path and os.path.exists(measurements_path)
        has_locations = location_checked_path and os.path.exists(location_checked_path)
        has_taxonomy = taxonomy_path and os.path.exists(taxonomy_path)
        has_barcodes = unit_barcodes_path and os.path.exists(unit_barcodes_path)
        has_geocodes = geocodes_path and os.path.exists(geocodes_path)
        has_mm_measurements = sizeratios_path and os.path.exists(sizeratios_path)

        tray_lookup_path = os.path.join(output_folder, "trays.csv")
        tray_df = generate_tray_lookup(
            trays_dir=trays_dir,
            specimens_dir=specimens_dir,
            barcode_csv_path=unit_barcodes_path,
            geocode_csv_path=geocodes_path,
            taxonomy_csv_path=taxonomy_path,
            labels_dir=labels_dir,
            output_path=None
        )

        specimen_path = os.path.join(output_folder, "specimens.csv")
        specimen_df = create_specimen_table(specimens_dir)

        if has_measurements:
            specimen_df = add_measurement_data(specimen_df, measurements_path, sizeratios_path)

        if has_locations:
            specimen_df = add_label_transcription(specimen_df, location_checked_path)

        if len(tray_df) > 0 and any(col in tray_df.columns for col in ['unit_barcode', 'geocode', 'full_taxonomy']):
            tray_info_cols = ['tray_id']
            for col in ['unit_barcode', 'geocode', 'full_taxonomy']:
                if col in tray_df.columns:
                    tray_info_cols.append(col)

            specimen_df = pd.merge(specimen_df, tray_df[tray_info_cols], on='tray_id', how='left')

            for col in tray_info_cols[1:]:
                specimen_df[col] = specimen_df[col].fillna("NA")

        specimen_df = add_data_completeness_flag(
            specimen_df,
            has_measurements=has_measurements,
            has_taxonomy=has_taxonomy,
            has_barcodes=has_barcodes,
            has_geocodes=has_geocodes,
            has_locations=has_locations,
            has_mm_measurements=has_mm_measurements
        )

        if 'data_complete' in specimen_df.columns and len(specimen_df) > 0:
            incomplete_data = specimen_df[specimen_df['data_complete'] == False].groupby('tray_id').size().reset_index(name='incomplete_specimen_count')
            all_trays = pd.DataFrame({'tray_id': tray_df['tray_id'].unique()})
            incomplete_data = pd.merge(all_trays, incomplete_data, on='tray_id', how='left')
            incomplete_data['incomplete_specimen_count'] = incomplete_data['incomplete_specimen_count'].fillna(0).astype(int)
            tray_df = pd.merge(tray_df, incomplete_data[['tray_id', 'incomplete_specimen_count']], on='tray_id', how='left')
            tray_df['incomplete_specimen_count'] = tray_df['incomplete_specimen_count'].fillna(0).astype(int)
            print(f"Added incomplete_specimen_count to tray lookup table")
        else:
            tray_df['incomplete_specimen_count'] = 0

        if 'mask_found' in specimen_df.columns and len(specimen_df) > 0:
            masked_data = specimen_df[specimen_df['mask_found'] == True].groupby('tray_id').size().reset_index(name='masked_specimen_count')
            all_trays = pd.DataFrame({'tray_id': tray_df['tray_id'].unique()})
            masked_data = pd.merge(all_trays, masked_data, on='tray_id', how='left')
            masked_data['masked_specimen_count'] = masked_data['masked_specimen_count'].fillna(0).astype(int)
            tray_df = pd.merge(tray_df, masked_data[['tray_id', 'masked_specimen_count']], on='tray_id', how='left')
            tray_df['masked_specimen_count'] = tray_df['masked_specimen_count'].fillna(0).astype(int)
            print(f"Added masked_specimen_count to tray lookup table")
        else:
            tray_df['masked_specimen_count'] = 0

        tray_df.to_csv(tray_lookup_path, index=False)
        print(f"Saved tray lookup table to {tray_lookup_path}")
        specimen_df.to_csv(specimen_path, index=False)
        print(f"Saved merged specimen data to {specimen_path}")

        summary_path = os.path.join(output_folder, "drawers.csv")
        summary_df = generate_drawer_summary(tray_df, specimen_df, summary_path)

        data_inputs_folder = os.path.join(output_folder, "data_inputs")
        os.makedirs(data_inputs_folder, exist_ok=True)

        input_files = [
            measurements_path,
            location_checked_path,
            taxonomy_path,
            unit_barcodes_path,
            geocodes_path,
            sizeratios_path
        ]
        input_file_names = [
            'measurements.csv',
            'location_checked.csv',
            'taxonomy.csv',
            'unit_barcodes.csv',
            'geocodes.csv',
            'sizeratios.csv'
        ]

        for path, name in zip(input_files, input_file_names):
            if path and os.path.exists(path):
                shutil.copy2(path, os.path.join(data_inputs_folder, name))
                print(f"Copied {name} to data_inputs folder")

        print(f"Data merge complete. Results saved to {output_folder}")
        return tray_df, specimen_df, summary_df

    except Exception as e:
        print(f"Error in merge_data: {str(e)}")
        raise
            
