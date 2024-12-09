import os
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def process_mask(mask_path, output_visual_path):
    try:
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            logger.error(f"Could not read mask: {mask_path}")
            return None, None
            
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, None
            
        contour = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect)
        area_px = cv2.contourArea(contour)
        
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.imshow(mask, cmap="gray")
        ax.plot(contour[:, 0, 0], contour[:, 0, 1], 'b-', label="Contour")
        ax.plot(np.append(box[:, 0], box[0, 0]), 
               np.append(box[:, 1], box[0, 1]), 'g--', 
               label=f"Length: {max(rect[1]):.1f}px")
        ax.legend(bbox_to_anchor=(0.5, -0.1), loc='upper center')
        ax.set_title(f"Area: {area_px:.0f}px²")
        ax.grid(True)
        
        os.makedirs(os.path.dirname(output_visual_path), exist_ok=True)
        plt.savefig(output_visual_path, bbox_inches="tight", dpi=150)
        plt.close(fig)
        
        return max(rect[1]), area_px
        
    except Exception as e:
        logger.error(f"Error processing {os.path.basename(mask_path)}: {e}")
        plt.close('all')
        return None, None

def generate_csv_with_visuals_and_measurements(input_dir, mask_dir, sizeratios_path, output_dir):
    try:
        os.makedirs(output_dir, exist_ok=True)
        output_visual_dir = os.path.join(output_dir, 'visuals')
        os.makedirs(output_visual_dir, exist_ok=True)

        sizeratios_df = pd.read_csv(sizeratios_path)
        sizeratios_map = sizeratios_df.set_index('drawer_id')['px_mm_ratio'].to_dict()

        file_info = []
        for root, _, files in os.walk(input_dir):
            for f in files:
                if f.endswith('.jpg') and 'checkpoint' not in f:
                    full_id = f.replace('.jpg', '')
                    drawer_id = full_id.split('_tray_')[0]
                    tray_id = '_spec_'.join(full_id.split('_spec_')[0].split('_tray_'))
                    
                    mask_path = os.path.join(mask_dir, drawer_id, tray_id, f"{full_id}.png")
                    file_info.append({
                        'spec_filename': f,
                        'full_id': full_id,
                        'drawer_id': drawer_id,
                        'tray_id': tray_id,
                        'mask_OK': 'Y' if os.path.exists(mask_path) else 'N',
                        'px_mm_ratio': sizeratios_map.get(drawer_id)
                    })

        df = pd.DataFrame(file_info)
        df['longest_px'] = pd.NA
        df['area_px'] = pd.NA
        df['spec_length_mm'] = pd.NA
        df['spec_area_mm2'] = pd.NA

        with ThreadPoolExecutor() as executor:
            futures = []
            for _, row in df.iterrows():
                if row['mask_OK'] == 'Y':
                    mask_path = os.path.join(mask_dir, row['drawer_id'], row['tray_id'], f"{row['full_id']}.png")
                    visual_path = os.path.join(output_visual_dir, row['drawer_id'], row['tray_id'])
                    os.makedirs(visual_path, exist_ok=True)
                    visual_path = os.path.join(visual_path, f"{row['full_id']}_measured.png")
                    futures.append((row['full_id'], executor.submit(process_mask, mask_path, visual_path)))

            for full_id, future in futures:
                try:
                    longest_px, area_px = future.result()
                    if longest_px and area_px:
                        idx = df[df['full_id'] == full_id].index[0]
                        ratio = df.at[idx, 'px_mm_ratio']
                        df.at[idx, 'longest_px'] = longest_px
                        df.at[idx, 'area_px'] = area_px
                        if ratio:
                            df.at[idx, 'spec_length_mm'] = longest_px / ratio
                            df.at[idx, 'spec_area_mm2'] = area_px / (ratio ** 2)
                except Exception as e:
                    logger.error(f"Error processing {full_id}: {e}")

        df['bad_size'] = df['spec_length_mm'].apply(lambda x: 'Y' if pd.notna(x) and x <= 5 else 'N')
        df['missing_size'] = df.apply(
            lambda row: 'Y' if row['mask_OK'] == 'Y' and pd.isna(row.get('spec_length_mm')) else 'N', 
            axis=1
        )

        cols = ['full_id', 'drawer_id', 'tray_id', 'spec_length_mm', 'spec_area_mm2',
                'longest_px', 'area_px', 'px_mm_ratio', 'mask_OK', 'missing_size', 'bad_size']
        
        df[cols].to_csv(os.path.join(output_dir, 'measurements.csv'), index=False)
        plt.close('all')
        return True

    except Exception as e:
        logger.error(f"Error generating measurements: {e}")
        plt.close('all')
        return False







