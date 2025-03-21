import os
import cv2
import numpy as np
from logging_utils import log, log_found, log_progress

def fix_single_mask(mask_path, current, total):
    """
    Fix a binary mask by keeping only the largest connected component.
    This helps with multi-part segmentations.
    
    Returns:
        bool: True if fixed, False if skipped or error
    """
    if 'checkpoint' in mask_path:
        return False
        
    try:
        mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask is None:
            log(f"Could not read {mask_path}")
            return False
            
        num_labels, labels = cv2.connectedComponents(mask)
        
        if num_labels <= 2:  # Only background and one component
            log_progress("fix_masks", current, total, f"Skipped (single component)")
            return False
        
        # Find the largest component
        largest_component = np.zeros_like(mask)
        max_size = 0
        
        for label in range(1, num_labels):
            component = (labels == label).astype(np.uint8) * 255
            size = np.sum(component)
            if size > max_size:
                max_size = size
                largest_component = component
        
        # Save the fixed mask
        cv2.imwrite(mask_path, largest_component)
        log_progress("fix_masks", current, total, f"Fixed {os.path.basename(mask_path)}")
        return True
            
    except Exception as e:
        log(f"Error processing {mask_path}: {str(e)}")
        return False

def fix_mask(mask_dir):
    """
    Fix all binary masks in the directory by keeping only the largest component in each.
    
    Args:
        mask_dir: Directory containing binary mask PNG files
    """
    # Find all mask files
    mask_files = []
    for root, _, files in os.walk(mask_dir):
        for f in files:
            if f.endswith('.png') and 'checkpoint' not in f:
                mask_path = os.path.join(root, f)
                mask_files.append(mask_path)
    
    if not mask_files:
        log("No mask files found to process")
        return
        
    log_found("mask files", len(mask_files))
    
    # Process each mask
    fixed = 0
    skipped = 0
    errors = 0
    
    for i, mask_path in enumerate(mask_files, 1):
        try:
            result = fix_single_mask(mask_path, i, len(mask_files))
            if result:
                fixed += 1
            else:
                skipped += 1
        except Exception as e:
            log(f"Error fixing {os.path.basename(mask_path)}: {str(e)}")
            errors += 1
    
    log(f"Complete. {fixed} fixed, {skipped} skipped, {errors} errors")