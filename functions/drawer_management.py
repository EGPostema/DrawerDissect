import os
import shutil
from pathlib import Path
from typing import List, Set
from logging_utils import log

def discover_and_sort_drawers(config) -> List[str]:
    """
    Discover images in unsorted directory, create drawer folders, and sort images.
    Returns list of drawer IDs that were processed.
    """
    unsorted_dir = config.unsorted_directory
    
    if not os.path.exists(unsorted_dir):
        log(f"Unsorted directory not found: {unsorted_dir}")
        return []
    
    # Find all images in unsorted directory
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    image_files = []
    
    for file in os.listdir(unsorted_dir):
        if file.lower().endswith(supported_formats):
            image_files.append(file)
    
    if not image_files:
        log("No images found in unsorted directory")
        return []
    
    log(f"Found {len(image_files)} images to sort")
    
    # Group images by drawer ID
    drawer_groups = {}
    for filename in image_files:
        # Extract drawer ID (filename without extension)
        drawer_id = os.path.splitext(filename)[0]
        if drawer_id not in drawer_groups:
            drawer_groups[drawer_id] = []
        drawer_groups[drawer_id].append(filename)
    
    log(f"Detected {len(drawer_groups)} drawers: {', '.join(drawer_groups.keys())}")
    
    # Sort images into drawer folders
    sorted_drawers = []
    for drawer_id, files in drawer_groups.items():
        log(f"Setting up drawer: {drawer_id}")
        
        # Create drawer directory structure
        config.setup_drawer_directories(drawer_id)
        
        # Move images to fullsize folder
        moved_count = 0
        for filename in files:
            if config.move_image_to_drawer(drawer_id, filename):
                moved_count += 1
        
        log(f"Moved {moved_count}/{len(files)} images for {drawer_id}")
        sorted_drawers.append(drawer_id)
    
    # Check if unsorted directory is now empty
    remaining_files = [f for f in os.listdir(unsorted_dir) 
                      if not f.startswith('.') and os.path.isfile(os.path.join(unsorted_dir, f))]
    
    if remaining_files:
        log(f"Warning: {len(remaining_files)} files remain in unsorted directory")
    else:
        log("All images successfully sorted into drawer folders")
    
    return sorted_drawers

def get_drawers_to_process(config, specified_drawers: List[str] = None) -> List[str]:
    """
    Determine which drawers to process based on:
    1. Specified drawers (command line)
    2. Existing drawer folders
    3. Images in unsorted directory
    """
    # First, sort any unsorted images
    newly_sorted = discover_and_sort_drawers(config)
    
    # Get all existing drawer folders
    existing_drawers = config.get_existing_drawers()
    all_available = sorted(set(existing_drawers + newly_sorted))
    
    if not all_available:
        log("No drawers found to process")
        return []
    
    # Filter by specified drawers if provided
    if specified_drawers:
        # Validate specified drawers exist
        invalid_drawers = [d for d in specified_drawers if d not in all_available]
        if invalid_drawers:
            log(f"Warning: Specified drawers not found: {', '.join(invalid_drawers)}")
        
        valid_drawers = [d for d in specified_drawers if d in all_available]
        if not valid_drawers:
            log("No valid drawers specified")
            return []
        
        log(f"Processing specified drawers: {', '.join(valid_drawers)}")
        return valid_drawers
    
    # Process all available drawers
    log(f"Processing all available drawers: {', '.join(all_available)}")
    return all_available

def is_specimen_only_drawer(config, drawer_id: str) -> bool:
    """
    Check if this is a specimen-only drawer (no fullsize images).
    
    Returns:
        bool: True if drawer only contains specimens, False if it's a standard drawer
    """
    fullsize_dir = config.get_drawer_directory(drawer_id, 'fullsize')
    specimens_dir = config.get_drawer_directory(drawer_id, 'specimens')
    
    # Check if fullsize has images
    supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
    
    fullsize_has_images = False
    if os.path.exists(fullsize_dir):
        fullsize_images = [f for f in os.listdir(fullsize_dir) 
                          if f.lower().endswith(supported_formats)]
        fullsize_has_images = len(fullsize_images) > 0
    
    specimens_has_images = False
    if os.path.exists(specimens_dir):
        specimens_images = [f for f in os.listdir(specimens_dir) 
                           if f.lower().endswith(supported_formats)]
        specimens_has_images = len(specimens_images) > 0
    
    # It's specimen-only if specimens exist but no fullsize images
    return specimens_has_images and not fullsize_has_images

def validate_drawer_structure(config, drawer_id: str) -> bool:
    """
    Validate that a drawer has the required directory structure.
    Create missing directories if needed.
    Handles both standard drawers and specimen-only drawers.
    """
    try:
        config.setup_drawer_directories(drawer_id)
        
        # Check if this is a specimen-only drawer
        if is_specimen_only_drawer(config, drawer_id):
            log(f"Detected specimen-only project: {drawer_id}")
            
            # For specimen-only, just check that specimens directory has images
            specimens_dir = config.get_drawer_directory(drawer_id, 'specimens')
            if not os.path.exists(specimens_dir):
                log(f"Warning: No specimens directory for project {drawer_id}")
                return False
            
            supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
            images = [f for f in os.listdir(specimens_dir) 
                     if f.lower().endswith(supported_formats)]
            
            if not images:
                log(f"Warning: No specimen images found in {specimens_dir}")
                return False
            
            return True
        
        # Standard drawer validation - check fullsize directory
        fullsize_dir = config.get_drawer_directory(drawer_id, 'fullsize')
        if not os.path.exists(fullsize_dir):
            log(f"Warning: No fullsize directory for drawer {drawer_id}")
            return False
        
        # Check for images in fullsize
        supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
        images = [f for f in os.listdir(fullsize_dir) 
                 if f.lower().endswith(supported_formats)]
        
        if not images:
            log(f"Warning: No images found in {fullsize_dir}")
            return False
        
        return True
        
    except Exception as e:
        log(f"Error validating drawer {drawer_id}: {str(e)}")
        return False
