import os
import cv2
import glob
import numpy as np
import pandas as pd
import random
from concurrent.futures import ThreadPoolExecutor
import logging
import matplotlib.pyplot as plt
from logging_utils import log

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

def should_create_visualizations(visualization_mode, existing_vis_count, total_masks):
    """
    Determine if visualizations should be created based on mode and existing count.
    
    Args:
        visualization_mode: "on", "off", or "rand_sample"
        existing_vis_count: Number of existing visualization files
        total_masks: Total number of masks being processed
        
    Returns:
        tuple: (should_create: bool, max_to_create: int or None)
    """
    if visualization_mode == "off":
        return False, 0
    elif visualization_mode == "on":
        return True, None  # Create all
    elif visualization_mode == "rand_sample":
        if existing_vis_count >= 20:
            log("Found 20+ existing visualizations, skipping random sampling")
            return False, 0
        else:
            remaining_needed = 20 - existing_vis_count
            return True, min(remaining_needed, total_masks)
    else:
        log(f"Unknown visualization mode: {visualization_mode}, defaulting to 'on'")
        return True, None

def select_random_masks(all_masks, max_count):
    """
    Randomly select masks for visualization.
    
    Args:
        all_masks: List of all mask file paths
        max_count: Maximum number to select
        
    Returns:
        List of selected mask paths
    """
    if len(all_masks) <= max_count:
        return all_masks
    
    return random.sample(all_masks, max_count)

def generate_csv_with_measurements(mask_dir, output_dir, csv_filename='measurements.csv', visualization_mode="on"):
    """
    Generate or update a CSV file of measurements for all valid masks.
    Skip already processed images and append data for new ones.
    Handles both standard specimen naming and custom filenames.
    
    Args:
        mask_dir: Directory containing mask PNG files
        output_dir: Directory to save the CSV output
        csv_filename: Name of the output CSV file
        visualization_mode: "on", "off", or "rand_sample" for visualization control
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
                        
                    # Try to extract drawer_id and tray_id from standard naming
                    # If it fails, use the filename as-is
                    if '_tray_' in full_id and '_spec' in full_id:
                        # Standard naming: drawer_id_tray_XX_spec_YY
                        drawer_id = full_id.split('_tray_')[0]
                        tray_id = full_id.split('_spec')[0]
                    else:
                        # Non-standard naming: use filename as full_id
                        # For drawer_id and tray_id, try to extract meaningful parts or use "unknown"
                        drawer_id = "custom_specimens"
                        tray_id = "custom_specimens"
                    
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
        
        # Handle visualizations based on mode
        vis_output_dir = os.path.join(output_dir, "visualizations")
        
        # Count existing visualizations
        existing_vis_count = 0
        if os.path.exists(vis_output_dir):
            existing_vis_count = len([f for f in os.listdir(vis_output_dir) 
                                    if f.endswith('_mapped.png')])
        
        # Determine if we should create visualizations
        should_create, max_to_create = should_create_visualizations(
            visualization_mode, existing_vis_count, len(updated_df)
        )
        
        if should_create:
            log(f"Generating visualizations in {vis_output_dir} (mode: {visualization_mode})")
            if max_to_create:
                log(f"Will create up to {max_to_create} visualizations")
            visualize_measurements(csv_path, mask_dir, vis_output_dir, 
                                 visualization_mode, max_to_create)
        else:
            log(f"Skipping visualizations (mode: {visualization_mode})")
        
    except Exception as e:
        logger.error(f"Error generating measurements: {e}")

def visualize_measurements(csv_path, mask_dir, output_dir, visualization_mode="on", max_visualizations=None):
    """
    Visualize the measurements for rows in the CSV.
    
    Args:
        csv_path: Path to the measurements CSV file
        mask_dir: Directory containing mask PNG files
        output_dir: Directory to save visualization images
        visualization_mode: "on", "off", or "rand_sample"
        max_visualizations: Maximum number of visualizations to create (for rand_sample mode)
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
        
        # Filter to only rows that have valid measurements and masks
        valid_rows = []
        for _, row in df.iterrows():
            full_id = row['full_id']
            if (full_id in mask_map and 
                not pd.isna(row.get('len1_px')) and 
                not pd.isna(row.get('len2_px'))):
                valid_rows.append(row)
        
        # Apply visualization mode selection
        if visualization_mode == "rand_sample" and max_visualizations:
            if len(valid_rows) > max_visualizations:
                valid_rows = random.sample(valid_rows, max_visualizations)
                log(f"Randomly selected {len(valid_rows)} specimens for visualization")
        
        total_rows = len(valid_rows)
        processed = 0
        skipped = 0
        
        # Process each selected row
        for row in valid_rows:
            full_id = row['full_id']
            mask_path = mask_map[full_id]
            
            # Create output path that mirrors the input directory structure
            rel_path = os.path.relpath(os.path.dirname(mask_path), mask_dir)
            output_subdir = os.path.join(output_dir, rel_path)
            os.makedirs(output_subdir, exist_ok=True)
            
            mapped_output_path = os.path.join(output_subdir, f"{full_id}_mapped.png")
            
            # Skip if already exists
            if os.path.exists(mapped_output_path):
                skipped += 1
                continue
            
            # Get measurements
            len1_px = row.get('len1_px')
            len2_px = row.get('len2_px')
            
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
                logger.info(f"Created {processed}/{total_rows} visualizations")
            
        log(f"Visualization complete. Created {processed} images, skipped {skipped}.")
        
    except Exception as e:
        logger.error(f"Error during visualization: {e}")
