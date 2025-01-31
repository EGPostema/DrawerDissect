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

def generate_csv_with_measurements(mask_dir, sizeratios_path, output_dir, csv_filename='measurements.csv'):
    """
    Generate or update a CSV file of measurements for all valid masks.
    Skip already processed images and append data for new ones.
    """
    try:
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
            
        # Initialize sizeratios_map based on metadata availability
        sizeratios_map = {}
        if sizeratios_path and os.path.isfile(sizeratios_path):
            sizeratios_df = pd.read_csv(sizeratios_path)
            sizeratios_map = sizeratios_df.set_index('drawer_id')['px_mm_ratio'].to_dict()
            logger.info(f"Loaded size ratios for {len(sizeratios_map)} drawers.")
        else:
            logger.info("No size ratios metadata available. Measurements will be in pixels only.")
            
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
                        'px_mm_ratio': sizeratios_map.get(drawer_id),
                        'mask_path': mask_path
                    })
                    
        df = pd.DataFrame(file_info)
        
        # Ensure required columns are present, even if DataFrame is empty
        required_columns = ['full_id', 'drawer_id', 'tray_id', 
                          'len1_mm', 'len2_mm', 'spec_area_mm2',
                          'len1_px', 'len2_px', 'area_px', 
                          'len1_points', 'len2_points', 
                          'px_mm_ratio', 'mask_OK', 'bad_size']
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
                        
                        # Add bad_size flag based on len1_px
                        df.at[idx, 'bad_size'] = 'Y' if len1_px < 50 else 'N'
                        
                        # Only calculate mm measurements if we have the ratio
                        ratio = df.at[idx, 'px_mm_ratio']
                        if ratio:
                            df.at[idx, 'len1_mm'] = len1_px / ratio
                            df.at[idx, 'len2_mm'] = len2_px / ratio
                            df.at[idx, 'spec_area_mm2'] = area_px / (ratio ** 2)
                except Exception as e:
                    logger.error(f"Error processing {full_id}: {e}")
                    
        # Concatenate new data with existing data
        cols = ['full_id', 'drawer_id', 'tray_id', 
                'len1_mm', 'len2_mm', 'spec_area_mm2',
                'len1_px', 'len2_px', 'area_px', 
                'len1_points', 'len2_points', 
                'px_mm_ratio', 'mask_OK', 'bad_size']
                
        new_df = df[cols]
        if not existing_df.empty:
            existing_df = existing_df.dropna(how='all', subset=cols)
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            updated_df = new_df
            
        updated_df.to_csv(csv_path, index=False)
        logger.info(f"Updated measurements saved to: {csv_path}")
    except Exception as e:
        logger.error(f"Error generating measurements: {e}")

def visualize_measurements(csv_path, mask_dir, output_dir=None, num_visualizations=10):
    """
    Visualize the measurements for the first few rows of the CSV.
    Saves visuals with lengths mapped as _mapped.png files.
    """
    try:
        # Load the CSV
        df = pd.read_csv(csv_path)
        
        # Default output directory to the CSV directory if not specified
        if output_dir is None:
            output_dir = os.path.dirname(csv_path)
        
        # Ensure the directory exists for outputs
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Perform a walkthrough to locate all mask files
        mask_files = glob.glob(os.path.join(mask_dir, "**", "*.png"), recursive=True)
        mask_map = {os.path.splitext(os.path.basename(mask))[0]: mask for mask in mask_files}
        
        # Process the first `num_visualizations` rows
        for _, row in df.head(num_visualizations).iterrows():
            full_id = row['full_id']
            mask_path = mask_map.get(full_id)
            mapped_output_path = os.path.join(output_dir, f"{full_id}_mapped.png")
            
            if not mask_path:
                logger.warning(f"Mask not found for {full_id}, skipping visualization.")
                continue

            len1_px = row['len1_px']
            len2_px = row['len2_px']
            if pd.isna(len1_px) or pd.isna(len2_px):
                logger.warning(f"Missing length measurements for {full_id}, skipping visualization.")
                continue
            
            # Read the mask
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            
            if mask is None:
                logger.warning(f"Could not read mask for {full_id}, skipping visualization.")
                continue

            # Create a figure
            plt.figure(figsize=(10, 10))
            plt.imshow(mask, cmap='gray')
            plt.title(f"{full_id}: len1_px={len1_px}, len2_px={len2_px}")
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
            logger.info(f"Saved visualization: {mapped_output_path}")

    except Exception as e:
        logger.error(f"Error during visualization: {e}")








