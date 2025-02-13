import os
import cv2
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def fix_single_mask(mask_path):
    if 'checkpoint' in mask_path:
        return
        
    try:
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            logger.error(f"Could not read {mask_path}")
            return
            
        num_labels, labels = cv2.connectedComponents(mask)
        
        if num_labels > 2:
            largest_component = np.zeros_like(mask)
            max_size = 0
            
            for label in range(1, num_labels):
                component = (labels == label).astype(np.uint8) * 255
                size = np.sum(component)
                if size > max_size:
                    max_size = size
                    largest_component = component
            
            cv2.imwrite(mask_path, largest_component)
            logger.info(f"Fixed: {os.path.basename(mask_path)}")
            
    except Exception as e:
        logger.error(f"Error processing {mask_path}: {str(e)}")

def fix_mask(mask_dir):
    for root, _, files in os.walk(mask_dir):
        for f in files:
            if f.endswith('.png') and 'checkpoint' not in f:
                mask_path = os.path.join(root, f)
                fix_single_mask(mask_path)