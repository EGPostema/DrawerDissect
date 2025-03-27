import os
import shutil
import pandas as pd
from datetime import datetime

def generate_tray_lookup(trays_dir, specimens_dir=None, barcode_csv_path=None, taxonomy_csv_path=None, labels_dir=None, output_path=None):
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
    
    if 'full_taxonomy' in tray_df.columns:
        column_order.append('full_taxonomy')
    
    if 'barcode_detect' in tray_df.columns:
        column_order.append('barcode_detect')
    
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
    Extracts drawer_id, tray_id, and full_id from filenames.
    
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
                
                # Extract drawer_id and tray_id using regex pattern
                match = re.match(r'(.+)_tray_(\d+)_spec_', full_id)
                if match:
                    drawer_id = match.group(1)
                    tray_num = match.group(2)
                    tray_id = f"{drawer_id}_tray_{tray_num}"
                else:
                    drawer_id = "MISSING"
                    tray_id = "MISSING"
                
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
        
        # Select required columns
        measurement_columns = [
            'full_id', 'len1_mm', 'len2_mm', 'spec_area_mm2',
            'len1_px', 'len2_px', 'mask_OK', 'bad_size'
        ]
        
        # If no mm measurements but we have sizeratios, try to calculate them
        if sizeratios_path and os.path.exists(sizeratios_path) and \
           'px_mm_ratio' not in measurements_df.columns and \
           ('len1_mm' not in measurements_df.columns or measurements_df['len1_mm'].isna().all()):
            try:
                sizeratios_df = pd.read_csv(sizeratios_path)
                sizeratios_map = sizeratios_df.set_index('drawer_id')['px_mm_ratio'].to_dict()
                
                # Add drawer_id if not present
                if 'drawer_id' not in measurements_df.columns:
                    drawer_pattern = r'(.+)_tray_\d+'
                    measurements_df['drawer_id'] = measurements_df['full_id'].str.extract(drawer_pattern)[0]
                
                # Add px_mm_ratio from sizeratios
                measurements_df['px_mm_ratio'] = measurements_df['drawer_id'].map(sizeratios_map)
                
                # Calculate mm measurements if px measurements exist
                if 'len1_px' in measurements_df.columns:
                    measurements_df['len1_mm'] = measurements_df.apply(
                        lambda row: row['len1_px'] / row['px_mm_ratio'] if pd.notnull(row['px_mm_ratio']) else None, 
                        axis=1
                    )
                if 'len2_px' in measurements_df.columns:
                    measurements_df['len2_mm'] = measurements_df.apply(
                        lambda row: row['len2_px'] / row['px_mm_ratio'] if pd.notnull(row['px_mm_ratio']) else None, 
                        axis=1
                    )
                if 'area_px' in measurements_df.columns:
                    measurements_df['spec_area_mm2'] = measurements_df.apply(
                        lambda row: row['area_px'] / (row['px_mm_ratio'] ** 2) if pd.notnull(row['px_mm_ratio']) else None, 
                        axis=1
                    )
                print(f"Calculated mm measurements using sizeratios from {sizeratios_path}")
            except Exception as e:
                print(f"Error calculating mm measurements: {str(e)}")
        
        # Ensure all required columns exist
        for col in measurement_columns:
            if col not in measurements_df.columns:
                print(f"Warning: Column '{col}' not found in measurements file")
                measurements_df[col] = None
        
        # Select only the columns we need
        measurements_df = measurements_df[measurement_columns]
        
        # Convert mask_OK to a simpler boolean-like column
        if 'mask_OK' in measurements_df.columns:
            measurements_df['mask_found'] = measurements_df['mask_OK'].apply(
                lambda x: True if x == 'Y' else False
            )
            measurements_df = measurements_df.drop('mask_OK', axis=1)
            measurement_columns.remove('mask_OK')
            measurement_columns.append('mask_found')
        
        # Convert bad_size to True/False for consistency
        if 'bad_size' in measurements_df.columns:
            measurements_df['bad_size'] = measurements_df['bad_size'].apply(
                lambda x: True if x == 'Y' else False
            )
        
        # Merge with specimen data
        merged_df = pd.merge(specimen_df, measurements_df, on='full_id', how='left')
        
        # Fill missing values
        for col in measurement_columns[1:]:  # Skip full_id
            if col in ['mask', 'bad_size']:
                merged_df[col] = merged_df[col].fillna(False)
            else:
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
        
        # Select required columns
        location_columns = [
            'filename', 'verbatim_text', 'proposed_location', 
            'validation_status', 'final_location', 'confidence_notes'
        ]
        
        # Ensure all required columns exist
        for col in location_columns:
            if col not in location_df.columns:
                print(f"Warning: Column '{col}' not found in location checked file")
                location_df[col] = None
        
        # Rename filename column to match spec_filename in specimen_df
        location_df = location_df.rename(columns={'filename': 'spec_filename'})
        
        # Merge with specimen data
        merged_df = pd.merge(specimen_df, location_df[location_columns], on='spec_filename', how='left')
        
        # Fill missing values
        for col in location_columns[1:]:  # Skip spec_filename
            merged_df[col] = merged_df[col].fillna("NA")
        
        print(f"Added label transcription data from {location_checked_path}")
        return merged_df
        
    except Exception as e:
        print(f"Error adding label transcription data: {str(e)}")
        return specimen_df

def add_data_completeness_flag(specimen_df, has_measurements=False, has_taxonomy=False, 
                         has_barcodes=False, has_locations=False):
    """
    Add a data_complete flag to the specimen DataFrame indicating whether
    all expected data for a specimen is available.
    
    Args:
        specimen_df (pd.DataFrame): DataFrame containing specimen information
        has_measurements (bool): Whether measurement data was added
        has_taxonomy (bool): Whether taxonomy data was added
        has_barcodes (bool): Whether barcode data was added
        has_locations (bool): Whether location data was added
        
    Returns:
        pd.DataFrame: Enhanced DataFrame with data_complete flag
    """
    # Create a copy to avoid modifying the original
    df = specimen_df.copy()
    
    # Initialize data_complete as True for all specimens
    df['data_complete'] = True
    
    # Check measurement completeness if applicable
    if has_measurements:
        # Check if any measurement is missing
        measurement_incomplete = (
            (df['len1_mm'] == -1) | 
            (df['len2_mm'] == -1) | 
            (df['spec_area_mm2'] == -1) |
            (~df['mask_found']) # Mask must exist
        )
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
              taxonomy_path=None, unit_barcodes_path=None, sizeratios_path=None,
              labels_dir=None, output_base_path=None):
    """
    Generate a complete merged dataset with information from all available sources.
    Creates three main outputs:
    1. Tray-level lookup table (trays.csv)
    2. Specimen-level merged dataset (merged_data.csv)
    3. Drawer-level summary (drawer_summary.csv)
    
    Args:
        specimens_dir (str): Directory containing specimen images
        measurements_path (str, optional): Path to the measurements CSV file
        location_checked_path (str, optional): Path to the location_checked CSV file
        taxonomy_path (str, optional): Path to the taxonomy CSV file
        unit_barcodes_path (str, optional): Path to the unit_barcodes CSV file
        sizeratios_path (str, optional): Path to the sizeratios CSV for px to mm conversion
        labels_dir (str, optional): Path to the labels directory
        output_base_path (str, optional): Base path for output directory
    
    Returns:
        tuple: (tray_df, specimen_df, summary_df) - The three main DataFrames created
    """
    try:
        # Create timestamped output folder
        timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M')
        output_folder = f"{output_base_path}_{timestamp}" if output_base_path else f"data_merge_{timestamp}"
        os.makedirs(output_folder, exist_ok=True)
        
        # Define paths to the trays directory
        trays_dir = os.path.join(os.path.dirname(specimens_dir), "trays")
        
        # Track what data sources are being added
        has_measurements = measurements_path and os.path.exists(measurements_path)
        has_locations = location_checked_path and os.path.exists(location_checked_path)
        has_taxonomy = taxonomy_path and os.path.exists(taxonomy_path)
        has_barcodes = unit_barcodes_path and os.path.exists(unit_barcodes_path)
        
        # 1. Generate Tray Lookup Table
        tray_lookup_path = os.path.join(output_folder, "trays.csv")
        tray_df = generate_tray_lookup(
            trays_dir=trays_dir,
            specimens_dir=specimens_dir,
            barcode_csv_path=unit_barcodes_path,
            taxonomy_csv_path=taxonomy_path,
            labels_dir=labels_dir,
            output_path=None  # Don't save yet, we'll add incomplete_data first
        )
        
        # 2. Create Specimen Table
        specimen_path = os.path.join(output_folder, "specimens.csv")
        specimen_df = create_specimen_table(specimens_dir)
        
        # Add measurement data if available
        if has_measurements:
            specimen_df = add_measurement_data(specimen_df, measurements_path, sizeratios_path)
            
        # Add label transcription data if available
        if has_locations:
            specimen_df = add_label_transcription(specimen_df, location_checked_path)
        
        # 3. Add tray-level information to specimen table
        # Add unit barcode and taxonomy if available
        if len(tray_df) > 0 and ('unit_barcode' in tray_df.columns or 'full_taxonomy' in tray_df.columns):
            # Get only the columns we need
            tray_info_cols = ['tray_id']
            if 'unit_barcode' in tray_df.columns:
                tray_info_cols.append('unit_barcode')
            if 'full_taxonomy' in tray_df.columns:
                tray_info_cols.append('full_taxonomy')
                
            # Merge with specimen data
            specimen_df = pd.merge(specimen_df, tray_df[tray_info_cols], on='tray_id', how='left')
            
            # Fill missing values
            for col in tray_info_cols[1:]:  # Skip tray_id
                specimen_df[col] = specimen_df[col].fillna("NA")
        
        # 4. Add data completeness flag
        specimen_df = add_data_completeness_flag(
            specimen_df,
            has_measurements=has_measurements,
            has_taxonomy=has_taxonomy,
            has_barcodes=has_barcodes,
            has_locations=has_locations
        )
        
        # 5. Add incomplete data count to the tray lookup table
        if 'data_complete' in specimen_df.columns and len(specimen_df) > 0:
            # Count incomplete specimens per tray
            incomplete_data = specimen_df[specimen_df['data_complete'] == False].groupby('tray_id').size().reset_index(name='incomplete_specimen_count')
            
            # Make sure all trays are included even if they have no incomplete specimens
            all_trays = pd.DataFrame({'tray_id': tray_df['tray_id'].unique()})
            incomplete_data = pd.merge(all_trays, incomplete_data, on='tray_id', how='left')
            incomplete_data['incomplete_specimen_count'] = incomplete_data['incomplete_specimen_count'].fillna(0).astype(int)
            
            # Update tray_df with incomplete counts
            tray_df = pd.merge(tray_df, incomplete_data[['tray_id', 'incomplete_specimen_count']], on='tray_id', how='left')
            tray_df['incomplete_specimen_count'] = tray_df['incomplete_specimen_count'].fillna(0).astype(int)
            
            print(f"Added incomplete_specimen_count to tray lookup table")
        else:
            tray_df['incomplete_specimen_count'] = 0
            
        # 6. Add masked_detected count to the tray lookup table
        if 'mask_found' in specimen_df.columns and len(specimen_df) > 0:
            # Count masked specimens per tray
            masked_data = specimen_df[specimen_df['mask_found'] == True].groupby('tray_id').size().reset_index(name='masked_specimen_count')
            
            # Make sure all trays are included even if they have no masked specimens
            all_trays = pd.DataFrame({'tray_id': tray_df['tray_id'].unique()})
            masked_data = pd.merge(all_trays, masked_data, on='tray_id', how='left')
            masked_data['masked_specimen_count'] = masked_data['masked_specimen_count'].fillna(0).astype(int)
            
            # Update tray_df with masked counts
            tray_df = pd.merge(tray_df, masked_data[['tray_id', 'masked_specimen_count']], on='tray_id', how='left')
            tray_df['masked_specimen_count'] = tray_df['masked_specimen_count'].fillna(0).astype(int)
            
            print(f"Added masked_specimen_count to tray lookup table")
        else:
            tray_df['masked_specimen_count'] = 0
            
        # Save the updated tray lookup table
        tray_df.to_csv(tray_lookup_path, index=False)
        print(f"Saved tray lookup table to {tray_lookup_path}")
        specimen_df.to_csv(specimen_path, index=False)
        print(f"Saved merged specimen data to {specimen_path}")
        
        # 5. Generate drawer-level summary
        summary_path = os.path.join(output_folder, "drawers.csv")
        summary_df = generate_drawer_summary(tray_df, specimen_df, summary_path)
        
        # 6. Copy input files to a data_inputs subfolder for reference
        data_inputs_folder = os.path.join(output_folder, "data_inputs")
        os.makedirs(data_inputs_folder, exist_ok=True)
        
        input_files = [
            measurements_path, 
            location_checked_path, 
            taxonomy_path, 
            unit_barcodes_path,
            sizeratios_path
        ]
        input_file_names = [
            'measurements.csv', 
            'location_checked.csv', 
            'taxonomy.csv', 
            'unit_barcodes.csv',
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


