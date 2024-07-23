import pandas as pd

def merge_datasets(label_dir, lengths_dir, pattern_csv_dir, output_file):
    # Load the datasets
    labels_df = pd.read_csv(label_dir)
    lengths_df = pd.read_csv(lengths_dir)
    patterns_df = pd.read_csv(pattern_csv_dir)
    
    # Drop 'spec_filename' from patterns_df if it exists
    if 'spec_filename' in patterns_df.columns:
        patterns_df.drop(columns=['spec_filename'], inplace=True)
    
    # Merge the datasets on 'tray_id'
    merged_df = pd.merge(lengths_df, labels_df, on='tray_id', how='inner', suffixes=('', '_y'))
    
    # Merge with the patterns dataset on 'full_id'
    final_merged_df = pd.merge(merged_df, patterns_df, on='full_id', how='inner', suffixes=('', '_z'))
    
    # Drop duplicate 'drawer_id' columns
    if 'drawer_id_y' in final_merged_df.columns:
        final_merged_df.drop(columns=['drawer_id_y'], inplace=True)
    
    # Ensure the column is named 'drawer_id'
    final_merged_df.rename(columns={'drawer_id': 'drawer_id'}, inplace=True)
    
    # Drop the 'json_filename' column if it exists
    if 'json_filename' in final_merged_df.columns:
        final_merged_df.drop(columns=['json_filename'], inplace=True)
    
    # Save the merged dataset to the output file
    final_merged_df.to_csv(output_file, index=False)
