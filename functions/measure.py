import os
import cv2
import glob
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import logging
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def get_lengths(contour):
    """
    Find len1 (maximum length) and len2 (longest perpendicular length) across the contour.
    Returns both lengths and their endpoints.
    """
    hull = cv2.convexHull(contour)
    hull_points = hull.reshape(-1, 2)
    
    # Find len1 (maximum length)
    max_distance = 0
    len1_points = None
    
    for i in range(len(hull_points)):
        for j in range(i + 1, len(hull_points)):
            dist = np.sqrt(np.sum((hull_points[i] - hull_points[j]) ** 2))
            if dist > max_distance:
                max_distance = dist
                len1_points = (hull_points[i], hull_points[j])
    
    # Calculate len2 (perpendicular to len1)
    if len1_points is None:
        return None, None, None, None
    
    # Get vector of len1
    len1_vector = len1_points[1] - len1_points[0]
    len1_unit = len1_vector / np.linalg.norm(len1_vector)
    
    # Find perpendicular direction
    perp_vector = np.array([-len1_unit[1], len1_unit[0]])
    
    # Find the maximum length perpendicular to len1
    max_perp_distance = 0
    len2_points = None
    
    for i in range(len(hull_points)):
        for j in range(i + 1, len(hull_points)):
            # Vector between current points
            vector = hull_points[j] - hull_points[i]
            
            # Project vector onto perpendicular direction
            projection = np.dot(vector, perp_vector)
            
            # Calculate actual distance
            dist = np.sqrt(np.sum((hull_points[i] - hull_points[j]) ** 2))
            
            # Check if points form a line roughly perpendicular to len1
            angle = np.abs(np.dot(vector / np.linalg.norm(vector), len1_unit))
            if angle < 0.1 and dist > max_perp_distance:  # angle close to 90 degrees
                max_perp_distance = dist
                len2_points = (hull_points[i], hull_points[j])
    
    return max_distance, len1_points, max_perp_distance, len2_points

def process_mask(mask_path):
    """
    Process a mask and calculate the measurements (len1, len2, and area).
    Returns lengths and their endpoints.
    """
    try:
        logger.info(f"Processing mask: {mask_path}")
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            logger.error(f"Could not read mask: {mask_path}")
            return None, None, None, None, None
            
        # Ensure mask is binary
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            logger.warning(f"No contours found in {mask_path}")
            return None, None, None, None, None
            
        contour = max(contours, key=cv2.contourArea)
        area_px = cv2.contourArea(contour)
        
        # Get both length measurements and endpoints
        len1_px, len1_points, len2_px, len2_points = get_lengths(contour)
        
        return len1_px, len1_points, len2_px, len2_points, area_px
    except Exception as e:
        logger.error(f"Error processing {os.path.basename(mask_path)}: {e}")
        return None, None, None, None, None

def generate_csv_with_measurements(mask_dir, output_dir, csv_filename='measurements.csv'):
    """
    Generate or update a CSV file of measurements for all valid masks.
    Skip already processed images and append data for new ones.
    
    Args:
        mask_dir: Directory containing mask PNG files
        output_dir: Directory to save the CSV output
        csv_filename: Name of the output CSV file
    """
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Ensure the output file path is valid
        csv_path = os.path.join(output_dir, csv_filename)
        
        # Load existing measurements if the CSV exists
        if os.path.exists(csv_path):
            existing_df = pd.read_csv(csv_path)
            processed_ids = set(existing_df['full_id'])
            logger.info(f"Loaded {len(processed_ids)} already processed images from CSV.")
        else:
            existing_df = pd.DataFrame()
            processed_ids = set()
            logger.info(f"No existing CSV found. Starting fresh.")
            
        file_info = []
        for root, _, files in os.walk(mask_dir):
            for f in files:
                if f.endswith('.png'):
                    mask_path = os.path.join(root, f)
                    full_id = f.replace('.png', '')
                    if full_id in processed_ids:
                        logger.info(f"Skipping already processed image: {full_id}")
                        continue
                        
                    # Extract drawer_id and tray_id
                    drawer_id = full_id.split('_tray_')[0]
                    tray_id = full_id.split('_spec')[0]
                    
                    file_info.append({
                        'spec_filename': f,
                        'full_id': full_id,
                        'drawer_id': drawer_id,
                        'tray_id': tray_id,
                        'mask_OK': 'Y',
                        'mask_path': mask_path
                    })
                    
        df = pd.DataFrame(file_info)
        
        # Ensure required columns are present, even if DataFrame is empty
        required_columns = ['full_id', 'drawer_id', 'tray_id', 
                          'len1_px', 'len2_px', 'area_px', 
                          'len1_points', 'len2_points', 
                          'mask_OK']
        for col in required_columns:
            if col not in df.columns:
                df[col] = pd.NA
                
        # Process masks with ThreadPoolExecutor
        with ThreadPoolExecutor() as executor:
            futures = []
            for _, row in df.iterrows():
                mask_path = row['mask_path']
                futures.append((row['full_id'], executor.submit(process_mask, mask_path)))
                
            for full_id, future in futures:
                try:
                    len1_px, len1_points, len2_px, len2_points, area_px = future.result()
                    if len1_px and len2_px and area_px:
                        idx = df[df['full_id'] == full_id].index[0]
                        df.at[idx, 'len1_px'] = len1_px
                        df.at[idx, 'len2_px'] = len2_px
                        df.at[idx, 'area_px'] = area_px
                        
                        # Save the endpoints as strings for later use
                        df.at[idx, 'len1_points'] = str(len1_points)
                        df.at[idx, 'len2_points'] = str(len2_points)
                    else:
                        # Mark as problematic mask if measurement failed
                        idx = df[df['full_id'] == full_id].index[0]
                        df.at[idx, 'mask_OK'] = 'N'
                        
                except Exception as e:
                    logger.error(f"Error processing {full_id}: {e}")
                    # Mark as problematic if exception occurred
                    idx = df[df['full_id'] == full_id].index[0]
                    df.at[idx, 'mask_OK'] = 'N'
                    
        # Concatenate new data with existing data
        cols = ['full_id', 'drawer_id', 'tray_id',
                'len1_px', 'len2_px', 'area_px', 
                'len1_points', 'len2_points', 
                'mask_OK']
                
        new_df = df[cols]
        
        if not existing_df.empty:
            # Ensure existing data has the same columns
            existing_cols = set(existing_df.columns)
            for col in cols:
                if col not in existing_cols:
                    existing_df[col] = pd.NA
            
            existing_df = existing_df.dropna(how='all', subset=cols)
            updated_df = pd.concat([existing_df[cols], new_df], ignore_index=True)
        else:
            updated_df = new_df
            
        updated_df.to_csv(csv_path, index=False)
        logger.info(f"Updated measurements saved to: {csv_path}")
        
        # Create visualizations
        vis_output_dir = os.path.join(output_dir, "visualizations")
        logger.info(f"Generating visualizations in {vis_output_dir}")
        visualize_measurements(csv_path, mask_dir, vis_output_dir)
        
    except Exception as e:
        logger.error(f"Error generating measurements: {e}")

def visualize_measurements(csv_path, mask_dir, output_dir):
    """
    Visualize the measurements for all rows in the CSV.
    Saves visuals with lengths mapped as _mapped.png files in a directory structure
    that mirrors the input mask directory.
    
    Args:
        csv_path: Path to the measurements CSV file
        mask_dir: Directory containing mask PNG files
        output_dir: Directory to save visualization images
    """
    try:
        # Load the CSV
        df = pd.read_csv(csv_path)
        
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Get a list of all mask files with their full paths
        mask_files = glob.glob(os.path.join(mask_dir, "**", "*.png"), recursive=True)
        
        # Create a mapping of full_id to mask path
        mask_map = {}
        for mask_path in mask_files:
            mask_filename = os.path.basename(mask_path)
            full_id = os.path.splitext(mask_filename)[0]
            mask_map[full_id] = mask_path
        
        # Count for progress reporting
        total_rows = len(df)
        processed = 0
        skipped = 0
        
        # Process each row in the CSV
        for _, row in df.iterrows():
            full_id = row['full_id']
            mask_path = mask_map.get(full_id)
            
            if not mask_path:
                logger.warning(f"Mask not found for {full_id}, skipping visualization.")
                skipped += 1
                continue
                
            # Get measurements
            len1_px = row.get('len1_px')
            len2_px = row.get('len2_px')
            
            if pd.isna(len1_px) or pd.isna(len2_px):
                logger.warning(f"Missing length measurements for {full_id}, skipping visualization.")
                skipped += 1
                continue
                
            # Create output path that mirrors the input directory structure
            rel_path = os.path.relpath(os.path.dirname(mask_path), mask_dir)
            output_subdir = os.path.join(output_dir, rel_path)
            os.makedirs(output_subdir, exist_ok=True)
            
            mapped_output_path = os.path.join(output_subdir, f"{full_id}_mapped.png")
            
            # Skip if already exists
            if os.path.exists(mapped_output_path):
                skipped += 1
                continue
                
            # Read the mask
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            
            if mask is None:
                logger.warning(f"Could not read mask for {full_id}, skipping visualization.")
                skipped += 1
                continue
                
            # Create a figure
            plt.figure(figsize=(10, 10))
            plt.imshow(mask, cmap='gray')
            plt.title(f"{full_id}: len1_px={len1_px:.1f}, len2_px={len2_px:.1f}")
            plt.axis('off')
            
            # Add length annotations
            try:
                if not pd.isna(row['len1_points']):
                    len1_points = eval(row['len1_points'], {"array": np.array, "int32": np.int32})
                    plt.plot([len1_points[0][0], len1_points[1][0]],
                             [len1_points[0][1], len1_points[1][1]], 'r-', linewidth=2, label='Length 1')
                    
                if not pd.isna(row['len2_points']):
                    len2_points = eval(row['len2_points'], {"array": np.array, "int32": np.int32})
                    plt.plot([len2_points[0][0], len2_points[1][0]],
                             [len2_points[0][1], len2_points[1][1]], 'b-', linewidth=2, label='Length 2')
                    
                plt.legend()
            except Exception as e:
                logger.warning(f"Error plotting lengths for {full_id}: {e}")
                
            plt.savefig(mapped_output_path, bbox_inches='tight', dpi=300)
            plt.close()
            
            processed += 1
            # Log progress every 10 images
            if processed % 10 == 0:
                logger.info(f"Processed {processed}/{total_rows} visualizations")
            
        logger.info(f"Visualization complete. Created {processed} visualization images, skipped {skipped}.")
        
    except Exception as e:
        logger.error(f"Error during visualization: {e}")








