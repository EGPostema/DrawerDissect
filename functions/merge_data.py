import os
import shutil
import pandas as pd
from datetime import datetime

def validate_columns(df, required_cols, dataset_name):
    """Validate that required columns exist in the dataframe."""
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"Missing columns in {dataset_name}: {missing}")
        return False
    return True

def generate_tray_id(series, column_name):
    """Extract tray_id from full specimen ID."""
    tray_ids = series.str.extract(r'(.*?)_spec')[0]
    failed_mask = tray_ids.isna()
    if failed_mask.any():
        print(f"Error extracting tray_id for {failed_mask.sum()} rows in {column_name}")
    return tray_ids

def extract_first_genus(taxonomy):
    """Extract the first genus from a full taxonomy string."""
    if pd.isna(taxonomy):
        return 'Unknown'
    return taxonomy.split()[0]

def generate_data_summary(df, available_data):
    """Generate a summary DataFrame with metrics per drawer_id based on available data."""
    # Ensure drawer_id is available
    if 'drawer_id' not in df.columns:
        if 'full_id' in df.columns:
            df['drawer_id'] = df['full_id'].str.extract(r'(.*?)_tray_')[0]
        elif 'tray_id' in df.columns:
            df['drawer_id'] = df['tray_id'].str.extract(r'(.*?)_tray_')[0]
        elif 'filename' in df.columns:
            # First get tray_id from filename
            tray_pattern = df['filename'].str.extract(r'(.*?)_spec_')[0]
            # Then get drawer_id from tray_id
            df['drawer_id'] = tray_pattern.str.extract(r'(.*?)_tray_')[0]
        else:
            df['drawer_id'] = 'unknown'
    
    # Define aggregate operations based on available data
    agg_dict = {}
    
    # Basic specimen count
    if 'full_id' in df.columns:
        agg_dict['full_id'] = 'count'  # Total specimens
    elif 'filename' in df.columns:
        agg_dict['filename'] = 'count'  # Total specimens
    
    # Tray count
    if 'tray_id' in df.columns:
        agg_dict['tray_id'] = 'nunique'  # Number of unique trays
    
    # Mask and size info
    if available_data['measurements']:
        if 'mask_OK' in df.columns:
            agg_dict['mask_OK'] = lambda x: (x == 'Y').mean() if 'Y' in x.values else 0
        if 'bad_size' in df.columns:
            agg_dict['bad_size'] = lambda x: (x == 'Y').mean() if 'Y' in x.values else 0
    
    # Perform the groupby aggregation
    summary = df.groupby('drawer_id').agg(agg_dict).reset_index()
    
    # Rename columns based on what's available
    renamed_columns = {'drawer_id': 'drawer_id'}
    if 'full_id' in agg_dict:
        renamed_columns['full_id'] = 'specimen_count'
    if 'filename' in agg_dict:
        renamed_columns['filename'] = 'specimen_count'
    if 'tray_id' in agg_dict:
        renamed_columns['tray_id'] = 'tray_count'
    if 'mask_OK' in agg_dict:
        renamed_columns['mask_OK'] = 'prop_masked'
    if 'bad_size' in agg_dict:
        renamed_columns['bad_size'] = 'prop_badsize'
    
    # Rename the columns
    summary.rename(columns=renamed_columns, inplace=True)
    
    # Add missing taxonomy and barcode counts (per unique tray)
    if available_data['taxonomy'] and 'tray_id' in df.columns and 'taxonomy_missing' in df.columns:
        # Count unique trays with missing taxonomy for each drawer
        tax_missing_counts = {}
        for drawer_id, drawer_df in df.groupby('drawer_id'):
            # Get unique tray_ids with missing taxonomy
            missing_trays = drawer_df[drawer_df['taxonomy_missing'] == 'Y']['tray_id'].unique()
            tax_missing_counts[drawer_id] = len(missing_trays)
        
        # Add to summary
        summary['tax_missing'] = summary['drawer_id'].map(tax_missing_counts).fillna(0).astype(int)
    
    if available_data['barcodes'] and 'tray_id' in df.columns and 'barcode_missing' in df.columns:
        # Count unique trays with missing barcodes for each drawer
        barcode_missing_counts = {}
        for drawer_id, drawer_df in df.groupby('drawer_id'):
            # Get unique tray_ids with missing barcodes
            missing_trays = drawer_df[drawer_df['barcode_missing'] == 'Y']['tray_id'].unique()
            barcode_missing_counts[drawer_id] = len(missing_trays)
        
        # Add to summary
        summary['barcode_missing'] = summary['drawer_id'].map(barcode_missing_counts).fillna(0).astype(int)
    
    # Add genera metrics if taxonomy data is available
    if available_data['taxonomy'] and 'full_taxonomy' in df.columns:
        # Filter out NA and MISSING before calculating unique genera
        summary['unique_genera'] = df.groupby('drawer_id')['full_taxonomy'].apply(
            lambda x: len(set(g for g in x.apply(extract_first_genus) if g not in ['Unknown', 'MISSING', 'NA']))
        ).values
        
        # Generate alphabetical, comma-separated list of genera, excluding NA and MISSING
        summary['genera_list'] = df.groupby('drawer_id')['full_taxonomy'].apply(
            lambda x: ', '.join(sorted(set(g for g in x.apply(extract_first_genus) 
                                          if g not in ['Unknown', 'MISSING', 'NA'])))
        ).values
    
    # Add location verification metric if location data is available
    if available_data['location'] and 'validation_status' in df.columns:
        summary['prop_locations_verif'] = df.groupby('drawer_id')['validation_status'].apply(
            lambda x: (x == 'VERIFIED').mean() if 'VERIFIED' in x.values else 0
        ).values
    
    return summary

def merge_data(measurements_path, location_checked_path, taxonomy_path, unit_barcodes_path, output_base_path, mode="FMNH"):
    try:
        # Create timestamped output folder
        timestamp = datetime.now().strftime('%d_%m_%Y_%H_%M')
        output_folder = f"{output_base_path}_{timestamp}"
        os.makedirs(output_folder, exist_ok=True)
        
        print(f"Created output folder: {output_folder}")

        # Check which data sources are available
        available_data = {
            'measurements': measurements_path and os.path.exists(measurements_path),
            'location': location_checked_path and os.path.exists(location_checked_path),
            'taxonomy': taxonomy_path and os.path.exists(taxonomy_path),
            'barcodes': unit_barcodes_path and os.path.exists(unit_barcodes_path)
        }
        
        print(f"Available data sources:")
        for src, avail in available_data.items():
            print(f"  {src}: {'Available' if avail else 'Not available'}")
        
        # Count the number of available data sources
        available_count = sum(available_data.values())
        
        # Decide whether to merge based on the formula
        should_merge = (available_count >= 2)
        
        # Decide whether to generate summary based on the formula
        should_summarize = (available_data['measurements'] or
                           available_data['taxonomy'] or
                           available_data['location'])
        if available_data['barcodes'] and available_count == 1:
            should_summarize = False  # No summary if only barcodes
            
        print(f"Will {'perform' if should_merge else 'skip'} data merge")
        print(f"Will {'generate' if should_summarize else 'skip'} summary")
        
        # If no data sources, exit early
        if available_count == 0:
            print("No data sources available for processing")
            return None
        
        # Copy available input files to the output folder
        input_files = []
        if available_data['measurements']:
            input_files.append((measurements_path, 'measurements.csv'))
        if available_data['location']:
            input_files.append((location_checked_path, 'location_checked.csv'))
        if available_data['taxonomy']:
            input_files.append((taxonomy_path, 'taxonomy.csv'))
        if available_data['barcodes']:
            input_files.append((unit_barcodes_path, 'unit_barcodes.csv'))
        
        for path, name in input_files:
            shutil.copy2(path, os.path.join(output_folder, name))
        
        print(f"Copied {len(input_files)} input files to output folder")
        
        # Load available datasets
        data = {}
        
        if available_data['measurements']:
            meas_df = pd.read_csv(measurements_path)
            # Remove point columns
            if 'len1_points' in meas_df.columns:
                meas_df.drop(columns=['len1_points'], inplace=True)
            if 'len2_points' in meas_df.columns:
                meas_df.drop(columns=['len2_points'], inplace=True)
            
            # Generate tray_id if not already present
            if 'tray_id' not in meas_df.columns and 'full_id' in meas_df.columns:
                meas_df['tray_id'] = generate_tray_id(meas_df['full_id'], 'full_id')
            
            data['measurements'] = meas_df
            print(f"Loaded measurements: {len(meas_df)} rows")
        
        if available_data['location']:
            loc_df = pd.read_csv(location_checked_path)
            
            # Generate full_id from filename by removing .jpg extension
            if 'filename' in loc_df.columns:
                loc_df['full_id'] = loc_df['filename'].str.replace('.jpg', '')
            
            # Generate tray_id if not already present
            if 'tray_id' not in loc_df.columns and 'filename' in loc_df.columns:
                loc_df['tray_id'] = generate_tray_id(loc_df['filename'], 'filename')
                
            data['location'] = loc_df
            print(f"Loaded location data: {len(loc_df)} rows")
        
        if available_data['taxonomy']:
            tax_df = pd.read_csv(taxonomy_path)
            # Rename taxonomy to full_taxonomy for consistency
            if 'taxonomy' in tax_df.columns:
                tax_df.rename(columns={'taxonomy': 'full_taxonomy'}, inplace=True)
            data['taxonomy'] = tax_df
            print(f"Loaded taxonomy data: {len(tax_df)} rows")
        
        if available_data['barcodes']:
            barcodes_df = pd.read_csv(unit_barcodes_path)
            data['barcodes'] = barcodes_df
            print(f"Loaded barcode data: {len(barcodes_df)} rows")
        
        # Result dataset to return
        result_df = None
        
        # Process based on the formulas provided
        if should_merge:
            # STEP 1: Start with measurements and/or locations
            if available_data['measurements'] and available_data['location']:
                # Both measurements and locations are available - merge them
                meas_df = data['measurements']
                loc_df = data['location']
                
                # Add spec_filename to measurements if needed for merge
                if 'spec_filename' not in meas_df.columns and 'full_id' in meas_df.columns:
                    meas_df['spec_filename'] = meas_df['full_id'] + '.jpg'
                
                # Merge measurements and locations on full_id
                result_df = pd.merge(
                    meas_df,
                    loc_df,
                    on='full_id',
                    how='outer',
                    suffixes=('', '_loc')
                )
                
                # Clean up duplicate columns
                columns_to_drop = [col for col in result_df.columns if col.endswith('_loc')]
                result_df.drop(columns=columns_to_drop, inplace=True)
                
            elif available_data['measurements']:
                # Only measurements available
                result_df = data['measurements'].copy()
                
            elif available_data['location']:
                # Only location available
                result_df = data['location'].copy()
            
            # STEP 2: Ensure tray_id is available
            if result_df is not None and 'tray_id' not in result_df.columns:
                if 'full_id' in result_df.columns:
                    result_df['tray_id'] = generate_tray_id(result_df['full_id'], 'full_id')
                    result_df['tray_id'] = result_df['tray_id'].astype(str)
            
            # STEP 3: Add taxonomy data if available
            if available_data['taxonomy'] and result_df is not None:
                tax_df = data['taxonomy']
                tax_df['tray_id'] = tax_df['tray_id'].astype(str)
                
                # Convert result_df tray_id to string for merge
                if 'tray_id' in result_df.columns:
                    result_df['tray_id'] = result_df['tray_id'].astype(str)
                    
                    # Left join to keep all specimens/trays from result_df
                    result_df = pd.merge(
                        result_df,
                        tax_df[['tray_id', 'full_taxonomy']],
                        on='tray_id',
                        how='left'
                    )
                    
                    # Fill missing taxonomy values with "MISSING"
                    result_df['full_taxonomy'] = result_df['full_taxonomy'].fillna("MISSING")
            
            # STEP 3: Add barcode data if available
            if available_data['barcodes'] and result_df is not None:
                barcode_df = data['barcodes']
                barcode_df['tray_id'] = barcode_df['tray_id'].astype(str)
                
                # Convert result_df tray_id to string for merge
                if 'tray_id' in result_df.columns:
                    result_df['tray_id'] = result_df['tray_id'].astype(str)
                    
                    # Left join to keep all specimens/trays from result_df
                    result_df = pd.merge(
                        result_df,
                        barcode_df[['tray_id', 'unit_barcode']],
                        on='tray_id',
                        how='left'
                    )
                    
                    # Fill missing barcode values with "MISSING"
                    result_df['unit_barcode'] = result_df['unit_barcode'].fillna("MISSING")
            
            # STEP 4: Add flag columns for missing taxonomy and barcodes
            if available_data['taxonomy'] and 'full_taxonomy' in result_df.columns:
                result_df['taxonomy_missing'] = result_df['full_taxonomy'].apply(lambda x: 'Y' if x == "MISSING" else 'N')
                
            if available_data['barcodes'] and 'unit_barcode' in result_df.columns:
                result_df['barcode_missing'] = result_df['unit_barcode'].apply(lambda x: 'Y' if x == "MISSING" else 'N')
                
            # STEP 5: Clean up the result dataframe
            if result_df is not None:
                # Define columns in the final output order
                final_columns_order = [
                    'full_id', 'drawer_id', 'tray_id', 
                    'unit_barcode', 'full_taxonomy', 
                    'len1_mm', 'len2_mm', 'spec_area_mm2', 
                    'len1_px', 'len2_px', 'area_px'
                ]
                
                # Add location columns if available
                location_columns = [
                    'verbatim_text', 'proposed_location', 'validation_status',
                    'final_location', 'confidence_notes'
                ]
                
                # Add flag columns at the end
                flag_columns = [
                    'barcode_missing', 'taxonomy_missing', 
                    'mask_OK', 'bad_size'
                ]
                
                # Add spec_filename if needed for reference
                if 'spec_filename' in result_df.columns:
                    location_columns.append('spec_filename')
                
                # Only include available columns
                available_columns = []
                for col in final_columns_order:
                    if col in result_df.columns:
                        available_columns.append(col)
                
                for col in location_columns:
                    if col in result_df.columns:
                        available_columns.append(col)
                
                for col in flag_columns:
                    if col in result_df.columns:
                        available_columns.append(col)
                
                # Extract drawer_id if not already present
                if 'drawer_id' not in result_df.columns:
                    if 'full_id' in result_df.columns:
                        result_df['drawer_id'] = result_df['full_id'].str.extract(r'(.*?)_tray_')[0]
                    elif 'tray_id' in result_df.columns:
                        result_df['drawer_id'] = result_df['tray_id'].str.extract(r'(.*?)_tray_')[0]
                
                # Reorder columns
                result_df = result_df[available_columns]
                
                # Fill missing values appropriately
                for col in result_df.columns:
                    if col in ['full_taxonomy', 'unit_barcode']:
                        result_df[col] = result_df[col].fillna("MISSING")
                    elif result_df[col].dtype in ['float64', 'int64']:
                        result_df[col] = result_df[col].fillna(-1)
                    else:
                        result_df[col] = result_df[col].fillna("NA")
                
                # Remove duplicates if possible
                if 'full_id' in result_df.columns:
                    before_dedup = len(result_df)
                    result_df = result_df.drop_duplicates(subset='full_id', keep='first')
                    after_dedup = len(result_df)
                    if before_dedup > after_dedup:
                        print(f"Removed {before_dedup - after_dedup} duplicate rows")
                
                # Save the merged data
                merged_path = os.path.join(output_folder, 'merged_data.csv')
                result_df.to_csv(merged_path, index=False)
                print(f"Saved merged data ({len(result_df)} rows) to {merged_path}")
        
        else:
            # No merge needed, use the single available dataset for summary
            if available_data['measurements']:
                result_df = data['measurements'].copy()
            elif available_data['taxonomy']:
                result_df = data['taxonomy'].copy()
            elif available_data['location']:
                result_df = data['location'].copy()
            elif available_data['barcodes']:
                result_df = data['barcodes'].copy()
        
        # Generate summary if needed
        if should_summarize and result_df is not None:
            summary = generate_data_summary(result_df, available_data)
            
            if not summary.empty:
                summary_path = os.path.join(output_folder, 'data_summary.csv')
                summary.to_csv(summary_path, index=False)
                print(f"Saved summary data ({len(summary)} drawers) to {summary_path}")
                
                # Display summary stats
                drawer_count = len(summary)
                print("\nSummary Statistics:")
                print(f"  Total Drawers: {drawer_count}")
                
                if 'specimen_count' in summary.columns:
                    specimen_count = summary['specimen_count'].sum()
                    print(f"  Total Specimens: {specimen_count}")
                
                if 'tray_count' in summary.columns:
                    tray_count = summary['tray_count'].sum()
                    print(f"  Total Trays: {tray_count}")
            else:
                print("Unable to generate summary: insufficient data")
        
        # Return appropriate results
        if should_merge:
            return result_df, summary if should_summarize else None
        else:
            return None, summary if should_summarize else None
    
    except Exception as e:
        print(f"Error in merge_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


