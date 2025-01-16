import os
import cv2
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def get_max_length(contour):
    """
    Find the maximum length across the contour and return both the length
    and the endpoints of the maximum length line.
    """
    hull = cv2.convexHull(contour)
    max_distance = 0
    max_points = None

    # Convert hull to point array
    hull_points = hull.reshape(-1, 2)

    # Find the farthest points
    for i in range(len(hull_points)):
        for j in range(i + 1, len(hull_points)):
            dist = np.sqrt(np.sum((hull_points[i] - hull_points[j]) ** 2))
            if dist > max_distance:
                max_distance = dist
                max_points = (hull_points[i], hull_points[j])

    return max_distance, max_points

def process_mask(mask_path):
    """
    Process a mask and calculate the measurements (longest dimension and area).
    """
    try:
        logger.info(f"Processing mask: {mask_path}")
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            logger.error(f"Could not read mask: {mask_path}")
            return None, None

        # Ensure mask is binary
        _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            logger.warning(f"No contours found in {mask_path}")
            return None, None

        contour = max(contours, key=cv2.contourArea)
        area_px = cv2.contourArea(contour)

        # Get maximum length and endpoints
        longest_px, endpoints = get_max_length(contour)

        return longest_px, area_px
    except Exception as e:
        logger.error(f"Error processing {os.path.basename(mask_path)}: {e}")
        return None, None

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
        required_columns = ['full_id', 'drawer_id', 'tray_id', 'spec_length_mm',
                          'spec_area_mm2', 'longest_px', 'area_px', 'px_mm_ratio', 
                          'mask_OK', 'bad_size']
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
                    longest_px, area_px = future.result()
                    if longest_px and area_px:
                        idx = df[df['full_id'] == full_id].index[0]
                        df.at[idx, 'longest_px'] = longest_px
                        df.at[idx, 'area_px'] = area_px
                        
                        # Add bad_size flag based on longest_px
                        df.at[idx, 'bad_size'] = 'Y' if longest_px < 50 else 'N'

                        # Only calculate mm measurements if we have the ratio
                        ratio = df.at[idx, 'px_mm_ratio']
                        if ratio:
                            df.at[idx, 'spec_length_mm'] = longest_px / ratio
                            df.at[idx, 'spec_area_mm2'] = area_px / (ratio ** 2)
                except Exception as e:
                    logger.error(f"Error processing {full_id}: {e}")

        # Concatenate new data with existing data
        cols = ['full_id', 'drawer_id', 'tray_id', 'spec_length_mm', 'spec_area_mm2',
                'longest_px', 'area_px', 'px_mm_ratio', 'mask_OK', 'bad_size']

        new_df = df[cols]
        if not existing_df.empty:
            # Add bad_size column to existing data if it doesn't exist
            if 'bad_size' not in existing_df.columns:
                existing_df['bad_size'] = existing_df['longest_px'].apply(
                    lambda x: 'Y' if x < 50 else 'N')
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            updated_df = new_df

        updated_df.to_csv(csv_path, index=False)
        logger.info(f"Updated measurements saved to: {csv_path}")
    except Exception as e:
        logger.error(f"Error generating measurements: {e}")







