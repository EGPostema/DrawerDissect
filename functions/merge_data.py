import pandas as pd
import os
from datetime import datetime

# Merge pattern data
def mergepattern(coloroptera_path, pattern_data_path, output_path):
    # Read the input CSVs
    coloroptera_data = pd.read_csv(coloroptera_path)
    pattern_data = pd.read_csv(pattern_data_path)

    # Perform the merge
    merged_data = pd.merge(coloroptera_data, pattern_data, on='full_id', how='outer', suffixes=('', '_pattern'))

    # Only fill NA values in the pattern columns
    pattern_cols = ['front_mac', 'mid_band', 'rear_mac', 'reduced_front', 'reduced_mid', 'reduced_rear',
                    'marginal_line', 'filled', 'immaculate', 'non_specimen']

    for col in pattern_cols:
        if col in merged_data.columns and f'{col}_pattern' in merged_data.columns:
            merged_data[col] = merged_data[col].combine_first(merged_data[f'{col}_pattern'])
            merged_data.drop(f'{col}_pattern', axis=1, inplace=True)

    # Filter out rows where 'full_id' contains 'checkpoint'
    merged_data_filtered = merged_data[~merged_data['full_id'].str.contains('checkpoint')]

    # Save the merged and filtered data to the output directory
    col_pattern_path = os.path.join(output_path, 'col_pattern.csv')
    merged_data_filtered.to_csv(col_pattern_path, index=False)

    # Log the success of the merge
    print(f"Merged pattern data saved to {col_pattern_path}")

# Merge length data
def mergelengths(col_pattern_path, lengths_path, output_path):
    col_pattern_data = pd.read_csv(col_pattern_path)
    lengths_data = pd.read_csv(lengths_path)

    # Perform the merge
    merged_data = pd.merge(col_pattern_data, lengths_data, on='full_id', how='outer', suffixes=('', '_length'))

    # Only fill NA values in the length columns
    length_cols = ['spec_l1_px', 'spec_l2_px', 'spec_area_px', 'img_height', 'img_width', 'logical_size']

    for col in length_cols:
        if col in merged_data.columns and f'{col}_length' in merged_data.columns:
            merged_data[col] = merged_data[col].combine_first(merged_data[f'{col}_length'])
            merged_data.drop(f'{col}_length', axis=1, inplace=True)

    # Filter out rows where 'full_id' contains 'checkpoint'
    merged_data_filtered = merged_data[~merged_data['full_id'].str.contains('checkpoint')]

    # Save the final merged data
    final_csv_path = os.path.join(output_path, 'merged.csv')
    merged_data_filtered.to_csv(final_csv_path, index=False)

    # Log the success of the final merge
    print(f"Final merged data saved to {final_csv_path}")

# Create timestamped folder for output files
def create_timestamped_folder(output_dir):
    timestamp = datetime.now().strftime('%m_%d_%Y_%H_%M_%S')
    output_path = os.path.join(output_dir, f'merged_output_{timestamp}')
    os.makedirs(output_path, exist_ok=True)

    # Log the creation of the folder
    print(f"Created output folder: {output_path}")
    
    return output_path

# Main function to run the merges
def merge_datasets(coloroptera_path, lengths_path, pattern_data_path, output_dir):
    # Create a timestamped folder for the output
    output_path = create_timestamped_folder(output_dir)

    # Run mergepattern
    mergepattern(coloroptera_path, pattern_data_path, output_path)

    # Run mergelengths using 'col_pattern.csv' from mergepattern
    col_pattern_path = os.path.join(output_path, 'col_pattern.csv')
    mergelengths(col_pattern_path, lengths_path, output_path)

    print(f"Data merged successfully and saved in folder: {output_path}")







