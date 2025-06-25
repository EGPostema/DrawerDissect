import yaml
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from logging_utils import log

class DrawerDissectConfig:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize config from YAML file."""
        self.config_path = Path(config_path)
        self._config = self._load_config()
        self._setup_base_directories()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load and parse the YAML configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found at {self.config_path}")
        
        with open(self.config_path) as f:
            return yaml.safe_load(f)
    
    def _setup_base_directories(self):
        """Create base directories (unsorted, etc.)."""
        base_dir = self._config.get('base_directory', '')
        unsorted_dir = os.path.join(base_dir, self._config['directories']['unsorted'])
        Path(unsorted_dir).mkdir(parents=True, exist_ok=True)
    
    def discover_drawers(self) -> List[str]:
        """Discover drawer IDs from images in unsorted directory."""
        unsorted_dir = self.unsorted_directory
        if not os.path.exists(unsorted_dir):
            return []
        
        drawer_ids = []
        supported_formats = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')
        
        for file in os.listdir(unsorted_dir):
            if file.lower().endswith(supported_formats):
                # Extract drawer ID by removing file extension
                drawer_id = os.path.splitext(file)[0]
                drawer_ids.append(drawer_id)
        
        return sorted(list(set(drawer_ids)))  # Remove duplicates and sort
    
    def get_existing_drawers(self) -> List[str]:
        """Get list of existing drawer folders."""
        drawers_base = os.path.dirname(self.unsorted_directory)
        if not os.path.exists(drawers_base):
            return []
        
        existing = []
        for item in os.listdir(drawers_base):
            item_path = os.path.join(drawers_base, item)
            if os.path.isdir(item_path) and item != 'unsorted':
                existing.append(item)
        
        return sorted(existing)
    
    def setup_drawer_directories(self, drawer_id: str):
        """Create all subdirectories for a specific drawer."""
        drawer_base = self.get_drawer_path(drawer_id)
        Path(drawer_base).mkdir(parents=True, exist_ok=True)
        
        for subdir in self._config['directories']['drawer_subdirs'].values():
            full_path = os.path.join(drawer_base, subdir)
            Path(full_path).mkdir(parents=True, exist_ok=True)
    
    def get_drawer_path(self, drawer_id: str) -> str:
        """Get the base path for a specific drawer."""
        base_dir = self._config.get('base_directory', '')
        drawers_base = os.path.dirname(os.path.join(base_dir, self._config['directories']['unsorted']))
        return os.path.join(drawers_base, drawer_id)
    
    def get_drawer_directory(self, drawer_id: str, subdir_key: str) -> str:
        """Get a specific subdirectory path for a drawer."""
        drawer_base = self.get_drawer_path(drawer_id)
        subdir = self._config['directories']['drawer_subdirs'][subdir_key]
        return os.path.join(drawer_base, subdir)
    
    def move_image_to_drawer(self, drawer_id: str, filename: str):
        """Move an image from unsorted to the appropriate drawer's fullsize folder."""
        src_path = os.path.join(self.unsorted_directory, filename)
        if not os.path.exists(src_path):
            return False
        
        # Ensure drawer directories exist
        self.setup_drawer_directories(drawer_id)
        
        # Move to fullsize folder
        dst_path = os.path.join(self.get_drawer_directory(drawer_id, 'fullsize'), filename)
        os.rename(src_path, dst_path)
        return True
    
    @property
    def unsorted_directory(self) -> str:
        """Get the unsorted directory path."""
        base_dir = self._config.get('base_directory', '')
        return os.path.join(base_dir, self._config['directories']['unsorted'])
    
    @property
    def api_keys(self) -> Dict[str, str]:
        """Get API keys from config."""
        return self._config['api_keys']
    
    @property
    def roboflow_models(self) -> Dict[str, Dict[str, Any]]:
        """Get Roboflow model configurations."""
        return self._config['roboflow']['models']
    
    @property
    def workspace(self) -> str:
        """Get Roboflow workspace name."""
        return self._config['roboflow']['workspace']
    
    @property
    def processing_flags(self) -> Dict[str, bool]:
        """Get processing toggle flags."""
        return self._config['processing']

    @property
    def prompts(self) -> Dict[str, Dict[str, str]]:
        """Get prompt configurations."""
        return self._config.get('prompts', {})
    
    def get_memory_config(self, step: str) -> Dict[str, Any]:
        """Get memory configuration for a specific step."""
        resources = self._config.get('resources', {})
        memory_config = resources.get('memory', {})
        step_overrides = memory_config.get('step_overrides', {})
        
        step_config = step_overrides.get(step, {})
        if step_config:
            return step_config
        
        default_config = {k: v for k, v in memory_config.items() 
                        if k not in ['step_overrides']}
        return default_config
